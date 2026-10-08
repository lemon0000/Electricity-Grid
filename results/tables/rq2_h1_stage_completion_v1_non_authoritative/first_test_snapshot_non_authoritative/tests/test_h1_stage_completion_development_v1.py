import json
from pathlib import Path

import pytest
from pyomo.environ import Constraint, Objective, Var, value
from pyomo.repn import generate_standard_repn

from experiments import h1_stage_completion_development_v1 as api
from tests.test_h1_native_raw_capture_development_v1 import FakeDirect
from tests.test_h1_linear_export_guard_development_v1 import Native, Handle, Expression
from tests.test_h1_native_raw_science_development_v1 import synthetic_channels, LIMITS
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver, saved, packet, spec


class SyntheticDirect(FakeDirect):
    def _presolve(self, model, **kwargs):
        self.model = model
        native, identity, cidentity = Native(), object(), object()
        variables = tuple(model.component_data_objects(Var))
        constraints = tuple(model.component_data_objects(Constraint, active=True))
        assignments = {n: float.fromhex(x) for n, x in self.report['assignment']}
        native.NumVars, native.NumConstrs = len(variables), len(constraints)
        native.variables = [Handle(identity, i, VarName='v'+str(i),
            VType='B' if v.is_binary() else 'I' if v.is_integer() else 'C',
            LB=float(v.value if v.fixed else v.lb) if v.fixed or v.lb is not None else -1e100,
            UB=float(v.value if v.fixed else v.ub) if v.fixed or v.ub is not None else 1e100,
            X=assignments[v.name]) for i, v in enumerate(variables)]
        by_name = {v.name: h for v, h in zip(variables, native.variables)}
        def expression(expr):
            repn = generate_standard_repn(expr, compute_values=True)
            return Expression([(by_name[v.name], float(c)) for v, c in zip(repn.linear_vars, repn.linear_coefs)], float(repn.constant))
        native.objective = expression(next(model.component_data_objects(Objective, active=True)).expr)
        native.constraints, native.rows = [], []
        for i, c in enumerate(constraints):
            row = expression(c.body)
            bound = float(value(c.lower if c.has_lb() else c.upper)) - row.constant
            row.constant = 0.
            native.rows.append(row)
            native.constraints.append(Handle(cidentity, i, Lazy=0, RHS=bound,
                Sense='=' if c.equality else '>' if c.has_lb() else '<'))
        native.Status, native.SolCount, native.MIPGap = 2, 1, 0.
        for n in ('ObjVal', 'ObjBound', 'ObjBoundC', 'Runtime'):
            setattr(native, n, float.fromhex(self.report['provenance']['native'][n]['hex']))
        native.update = lambda: None
        vf, cf = tuple(zip(variables, native.variables)), tuple(zip(constraints, native.constraints))
        self.args = dict(variable_forward=vf, variable_reverse=tuple((h, v) for v, h in vf),
            constraint_forward=cf, constraint_reverse=tuple((h, c) for c, h in cf))
        self.native = native
        _, self.results = synthetic_channels(model, self.report, 'a'*64, 'b'*64)
        super()._presolve(model, **kwargs)

    def _postsolve(self):
        super()._postsolve()
        return self.results


@pytest.fixture
def setup_case(tmp_path, monkeypatch, saved, no_solver):
    def setup(fault=None, name='stage'):
        owner = api.OwnedStage(tmp_path/name, packet(), spec(), LIMITS, 0, ())
        solver = SyntheticDirect(None, None, None, owner.root, fault)
        solver.report = json.loads(saved[1][0])
        monkeypatch.setattr(api.capture, 'GurobiDirect', SyntheticDirect)
        monkeypatch.setattr(api.capture.old.provenance.adapter, 'create_solver',
            lambda specification: (solver, api.capture.old.audit.solver_options(specification)))
        return owner, solver
    return setup


def replay(owner, receipt):
    return api.inspect(owner.root, *owner.context,
        expected_producer_complete_sha=receipt.producer_complete_sha256,
        expected_science_terminal_sha=receipt.science_terminal_sha256)


def test_owned_return_and_fresh_reader_have_distinct_types(setup_case):
    owner, solver = setup_case()
    receipt = owner.run()
    assert type(receipt) is api.Completion and owner.complete and not owner.poisoned
    assert solver.apply_calls == solver.close_calls == 1
    assert len(list(owner.root.rglob('*'))) == 20  # 17 files + 3 nested directories
    assert not any(dict(receipt.authority_flags).values())
    result = replay(owner, receipt)
    assert result['result']['lock'] == 20.
    assert result['producer_completion_record_checked']
    assert not result['producer_run_return_observed']
    assert not result['whole_job_quiescence_checked']
    with pytest.raises(TypeError): api.Completion(owner.root, 'a'*64, 'b'*64, 'c'*64, 'd'*64)
    with pytest.raises(ValueError): owner.run()
    with pytest.raises(FileExistsError): api.OwnedStage(owner.root, *owner.context)
    assert solver.apply_calls == 1


@pytest.mark.parametrize('target', ['close', 'raw_terminal', 'complete'])
@pytest.mark.parametrize('after_write', [False, True])
def test_after_science_failure_never_returns_live_receipt(setup_case, monkeypatch, target, after_write):
    owner, solver = setup_case('close' if target == 'close' else None)
    original = api.io.write_metadata
    def fail(path, doc):
        chosen = (target == 'complete' and path == owner.root/'complete.json' or
                  target == 'raw_terminal' and path == owner.root/'native_raw/terminal.json')
        if chosen:
            if after_write: original(path, doc)
            raise OSError('injected confirmation failure')
        return original(path, doc)
    monkeypatch.setattr(api.io, 'write_metadata', fail)
    returned = []
    with pytest.raises((RuntimeError, OSError)): returned.append(owner.run())
    assert returned == [] and owner.poisoned and not owner.complete
    assert (owner.root/'science/terminal.json').exists()
    assert (owner.root/'native_raw/000/raw.bin').exists()
    if target == 'complete': assert (owner.root/'complete.json').exists() == after_write
    if target == 'raw_terminal': assert (owner.root/'native_raw/terminal.json').exists() == after_write
    assert solver.close_calls == 1
    with pytest.raises(ValueError): owner.run()
    assert solver.apply_calls == 1


@pytest.mark.parametrize('fault', ['poisoned', 'raw_poisoned', 'raw_unclosed', 'return_copy', 'fresh_failure'])
def test_post_return_state_or_replay_failure_no_receipt(setup_case, monkeypatch, fault):
    owner, _ = setup_case()
    original = api.capture.StageCapture.run
    def corrupt(producer, *args):
        answer = original(producer, *args)
        if fault == 'poisoned': producer.poisoned = True
        elif fault == 'raw_poisoned': producer.raw.poisoned = True
        elif fault == 'raw_unclosed': producer.raw.closed = False
        elif fault == 'return_copy': return dict(answer)
        elif fault == 'fresh_failure': (producer.root/'complete.json').write_bytes(b'{}')
        return answer
    monkeypatch.setattr(api.capture.StageCapture, 'run', corrupt)
    with pytest.raises(ValueError): owner.run()
    assert owner.poisoned and not owner.complete


@pytest.mark.parametrize('filename', ['complete.json', 'native_raw/terminal.json', 'science/terminal.json'])
def test_mid_replay_completion_record_drift(setup_case, monkeypatch, filename):
    import os
    owner, _ = setup_case(); receipt = owner.run()
    original = api.science.inspect
    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        path = owner.root/filename; stamp = path.stat(); raw = path.read_bytes()
        path.write_bytes(raw.replace(b'false', b' true', 1) if b'false' in raw else raw.replace(b'complete', b'corrupt!', 1))
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        return result
    monkeypatch.setattr(api.science, 'inspect', mutate)
    with pytest.raises(ValueError): replay(owner, receipt)


@pytest.mark.parametrize('fault', ['extra', 'missing', 'wrong_pin', 'wrong_request', 'foreign_native_path'])
def test_topology_context_and_external_pin_reject(setup_case, fault):
    owner, _ = setup_case(); receipt = owner.run()
    if fault == 'extra': (owner.root/'extra').mkdir()
    elif fault == 'missing': (owner.root/'complete.json').rename(owner.root/'retained_complete.json')
    elif fault == 'wrong_request': owner.context = (*owner.context[:3], 1, (20.,))
    elif fault == 'foreign_native_path':
        path = owner.root/'science/intent.json'; doc = json.loads(path.read_bytes())
        doc['native_path'] = str(owner.root/'foreign/raw.bin'); path.write_bytes(api.io.encode(doc))
    if fault == 'wrong_pin':
        with pytest.raises(ValueError): api.inspect(owner.root, *owner.context,
            expected_producer_complete_sha='a'*64, expected_science_terminal_sha=receipt.science_terminal_sha256)
    else:
        with pytest.raises(ValueError): replay(owner, receipt)


def test_reentry_and_owner_identity_reject_before_apply(setup_case):
    owner, solver = setup_case()
    owner.guard.acquire()
    try:
        with pytest.raises(ValueError): owner.run()
    finally: owner.guard.release()
    owner.owner = (-1, -1)
    with pytest.raises(ValueError): owner.run()
    assert owner.poisoned and solver.apply_calls == 0


def test_implementation_drift_during_fresh_inspection_rejects(setup_case, monkeypatch):
    owner, _ = setup_case(); receipt = owner.run()
    original = api.science.inspect
    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        monkeypatch.setattr(api, 'implementation_identity', lambda: 'f'*64)
        return result
    monkeypatch.setattr(api.science, 'inspect', mutate)
    with pytest.raises(ValueError): replay(owner, receipt)
