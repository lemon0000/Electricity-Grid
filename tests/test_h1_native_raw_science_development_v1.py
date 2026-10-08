from copy import deepcopy
from dataclasses import asdict
import json
from types import SimpleNamespace

import pytest
from pyomo.environ import value
from pyomo.opt import SolverResults, SolverStatus, TerminationCondition, SolutionStatus, ProblemSense

from experiments import h1_native_raw_science_development_v1 as api
from tests.test_h1_linear_export_guard_development_v1 import Expression
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver, saved, packet, spec

LIMITS = api.prior.H1HourReplayLimits(232, 891, 1272)


def model_for(p, index, locks):
    a = api.prior.native.model_api
    r = a.H1StageRequest(p.inputs, locks)
    return a.build_h1_stage_model(r, expected_identity=a.h1_stage_identity(r))


def synthetic_channels(model, old_report, binding, export):
    """Derived views from saved values, NOT historical native capsule evidence."""
    variables, count, _, _ = api.capture.export._canonical(model)
    assignment = {n: float.fromhex(x) for n, x in old_report['assignment']}
    handles, pairs = {}, []
    for i, var in enumerate(variables):
        lo, hi = (var.value, var.value) if var.fixed else (var.lb, var.ub)
        h = SimpleNamespace(index=i, VarName='v'+str(i), VType='B' if var.is_binary() else 'I' if var.is_integer() else 'C',
            LB=-1e100 if lo is None else float(value(lo)), UB=1e100 if hi is None else float(value(hi)), X=assignment[var.name])
        handles[var.name] = h
        pairs.append((var, h))
    p = old_report['provenance']
    native = SimpleNamespace(Status=p['native_status'], SolCount=p['native_solution_count'], ModelSense=1,
                             NumVars=len(variables), NumConstrs=count, MIPGap=0.)
    for name in ('ObjVal', 'ObjBound', 'ObjBoundC', 'Runtime'):
        setattr(native, name, float.fromhex(p['native'][name]['hex']))
    expression = Expression([(handles[n], float.fromhex(c)) for n, c, _ in p['ordered_native_objective_terms']],
                            float.fromhex(p['native_constant_hex']))
    # Capture only uses getVar(index).index, so no live native handles are needed.
    native.getObjective = lambda: expression
    raw = api.capture._capture(native, tuple(pairs), binding=binding, export_sha=export, apply_error=None)
    results = SolverResults()
    results.solver.status = SolverStatus[p['pyomo_status']]
    results.solver.termination_condition = TerminationCondition[p['pyomo_termination']]
    results.problem.sense = ProblemSense.minimize
    results.problem.lower_bound = float.fromhex(p['pyomo_lower_hex'])
    results.problem.upper_bound = float.fromhex(p['pyomo_upper_hex'])
    solution = results.solution.add()
    solution._cuid = False
    solution.status = SolutionStatus[p['pyomo_solution_status']]
    for name, number in assignment.items(): solution.variable[name] = {'Value': number}
    return raw, results


def sample(saved, index=0, p=None, locks=None):
    p = packet() if p is None else p
    locks = tuple(saved[0]['projection']['canonical_locks'][:index]) if locks is None else locks
    locks = tuple(float.fromhex(x) if isinstance(x, str) else x for x in locks)
    model = model_for(p, index, locks)
    report = json.loads(saved[1][index])
    key = api.request_key(p, spec(), LIMITS, index, locks)
    raw, results = synthetic_channels(model, report, 'a'*64, 'b'*64)
    post = api.capture_postsolve(model, results, native_sha=api.io.digest(raw), key=key)
    return p, locks, model, raw, post, results, key


def audit(s, raw=None, post=None, index=0):
    p, locks, model, original, sidecar, results, key = s
    return api.audit_stage(original if raw is None else raw, sidecar if post is None else post,
        p, spec(), LIMITS, index, locks, expected_key=key, expected_binding='a'*64, expected_export='b'*64)


@pytest.mark.parametrize('index', [0, 1, 2])
def test_three_stage_science_matches_saved_legacy_numerics(saved, index):
    s = sample(saved, index)
    result = audit(s, index=index)
    old = api.prior._audit_stage(s[0], spec(), LIMITS, index, s[1], saved[1][index])
    assert result['lock'].hex() == old['lock'].hex()
    assert result['assignment'] == old['assignment']
    assert result['generation_mapping'] == old['generation_mapping']
    assert result['numeric']['candidate_numeric_predicate_passed']
    assert result['numerical']['evidence_role'] == 'derived_legacy_predicate_view'
    assert not any(result[k] for k in api.capture.FLAGS)
    with pytest.raises(api.prior.H1ReportAuditRejected):
        api.prior._audit_stage(s[0], spec(), LIMITS, index, s[1], api.io.encode(result['numerical']))


@pytest.mark.parametrize('fault', ['bits', 'duplicate', 'index', 'bound', 'domain', 'coefficient',
    'constant', 'status', 'objective_value', 'binding', 'flag', 'extra', 'nonfinite'])
def test_capsule_corruption_rejects(saved, fault):
    s = sample(saved)
    doc = json.loads(s[3])
    if fault == 'bits':
        atom = doc['variables'][0]['attributes']['X']['atom']
        atom['bits'] = format(int(atom['bits'], 16) ^ 1, '016x')
    elif fault == 'duplicate': doc['variables'][1] = deepcopy(doc['variables'][0])
    elif fault == 'index': doc['variables'][0]['attributes']['index']['atom']['value'] = -1
    elif fault == 'bound': doc['variables'][0]['attributes']['UB']['atom'] = api.capture._atom(999.)
    elif fault == 'domain': doc['variables'][0]['attributes']['VType']['atom']['value'] = 'S'
    elif fault == 'coefficient': doc['objective']['terms'][0]['coefficient']['atom'] = api.capture._atom(99.)
    elif fault == 'constant': doc['objective']['constant']['atom'] = api.capture._atom(99.)
    elif fault == 'status': doc['attributes']['Status']['atom']['value'] = 9
    elif fault == 'objective_value': doc['attributes']['ObjVal']['atom'] = api.capture._atom(99.)
    elif fault == 'binding': doc['binding_sha256'] = 'c'*64
    elif fault == 'flag': doc['formal_result'] = True
    elif fault == 'extra': doc['extra'] = None
    else: doc['variables'][0]['attributes']['X']['atom'] = api.capture._atom(float('nan'))
    raw = api.io.encode(doc)
    side = json.loads(s[4]); side['native_sha256'] = api.io.digest(raw)
    with pytest.raises(ValueError): audit(s, raw, api.io.encode(side))


@pytest.mark.parametrize('fault', ['reported', 'completion', 'lower', 'sense', 'count', 'status', 'extra'])
def test_sidecar_corruption_rejects(saved, fault):
    s = sample(saved); doc = json.loads(s[4])
    if fault == 'reported': doc['reported_values'][0][1] = (999.).hex()
    elif fault == 'completion': doc['completions'].append(['foreign', (0.).hex(), 'canonical_fixed_constant'])
    elif fault == 'lower': doc['lower'] = (999.).hex()
    elif fault == 'sense': doc['sense'] = 'maximize'
    elif fault == 'count': doc['solution_records'] = True
    elif fault == 'status': doc['solution_status'] = 'feasible'
    else: doc['extra'] = None
    with pytest.raises(ValueError): audit(s, post=api.io.encode(doc))


def durable_source(tmp_path, saved, *, key_override=None):
    p, locks, model, raw, post, results, key = sample(saved)
    owner = api.capture.StageCapture(tmp_path/'producer', request_sha256=key if key_override is None else key_override,
        expected_structure=api.capture.old.audit._structure(model), expected_implementation=api.capture.implementation_identity())
    spec_sha = api.io.write_metadata(owner.root/'specification.json', dict(specification=asdict(spec()),
        options=api.capture.old.audit.solver_options(spec()), binding_sha256=owner.binding_sha))
    variables, count, _, _ = api.capture.export._canonical(model)
    export = api.io.write_metadata(owner.root/'export.json', dict(binding_sha256=owner.binding_sha,
        specification_sha256=spec_sha, model_structure=owner.expected_structure,
        result=dict(schema='h1_linear_export_guard_development_v1', variables=len(variables), constraints=count,
            exact_linear_correspondence_checked=True, native_export_coverage=False,
            native_execution_authenticated=False, resource_admission=False, formal_execution_ready=False, formal_result=False)))
    raw, results = synthetic_channels(model, json.loads(saved[1][0]), owner.binding_sha, export)
    owner.raw.deliver(0, lambda: raw, lambda data: data)
    return owner, export, raw, results, model, p, locks


def consume(tmp_path, d):
    owner, export, raw, results, model, p, locks = d
    return api.consume(tmp_path/'science', owner.raw.root/'000/raw.bin', results, model,
        p, spec(), LIMITS, 0, locks, expected_native_sha=api.io.digest(raw),
        expected_binding=owner.binding_sha, expected_export=export)


def test_durable_sidecar_precedes_science_and_fresh_replay(tmp_path, saved, monkeypatch):
    d = durable_source(tmp_path, saved)
    original = api.audit_stage
    calls = []
    def observed(*args, **kwargs):
        assert (tmp_path/'science/postsolve.bin').exists()
        assert (tmp_path/'science/postsolve_receipt.json').exists()
        calls.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(api, 'audit_stage', observed)
    result = consume(tmp_path, d)
    assert len(calls) == 2 and result['result']['lock'] == 20.
    assert not result['stage_capture_completion_checked']
    assert not (d[0].root/'complete.json').exists()
    replay = api.inspect(tmp_path/'science', d[5], spec(), LIMITS, 0, d[6],
                         expected_terminal_sha=result['terminal_sha256'])
    assert replay['assignment'] == result['result']['assignment']
    with pytest.raises(FileExistsError): consume(tmp_path, d)


@pytest.mark.parametrize('fault', ['receipt', 'science', 'terminal'])
def test_failure_keeps_native_and_sidecar_without_science_terminal(tmp_path, saved, monkeypatch, fault):
    d = durable_source(tmp_path, saved)
    original = api.io.write_metadata
    def write(path, doc):
        if path.name == ('postsolve_receipt.json' if fault == 'receipt' else 'terminal.json'):
            raise OSError('injected write failure')
        return original(path, doc)
    if fault == 'science': monkeypatch.setattr(api, 'audit_stage', lambda *a, **k: (_ for _ in ()).throw(ValueError('audit failed')))
    else: monkeypatch.setattr(api.io, 'write_metadata', write)
    with pytest.raises((OSError, ValueError)): consume(tmp_path, d)
    assert (d[0].raw.root/'000/raw.bin').read_bytes() == d[2]
    assert (tmp_path/'science/postsolve.bin').exists()
    assert not (tmp_path/'science/terminal.json').exists()


@pytest.mark.parametrize('filename', ['postsolve.bin', 'numerical.bin', 'mapping.bin', 'result.bin', 'intent.json'])
def test_fresh_replay_rejects_science_mutation(tmp_path, saved, filename):
    d = durable_source(tmp_path, saved); result = consume(tmp_path, d)
    (tmp_path/'science'/filename).write_bytes(b'{}')
    with pytest.raises(ValueError):
        api.inspect(tmp_path/'science', d[5], spec(), LIMITS, 0, d[6], expected_terminal_sha=result['terminal_sha256'])


def test_projection_rejection_retains_exact_receipt(tmp_path, saved, monkeypatch):
    d = durable_source(tmp_path, saved)
    receipt = {'status': 'rejected', 'changes': [['generation[fixture]', (-1e-12).hex(), (0.).hex()]]}
    error = api.prior.generation_projection.ProjectionRejected('injected rejection', receipt)
    def reject(*args, **kwargs):
        raise error
    monkeypatch.setattr(api, 'audit_stage', reject)
    with pytest.raises(api.prior.generation_projection.ProjectionRejected) as caught:
        consume(tmp_path, d)
    assert caught.value is error
    assert (tmp_path/'science/mapping.bin').read_bytes() == api.io.encode(receipt)
    assert (tmp_path/'science/postsolve_receipt.json').exists()
    assert (d[0].raw.root/'000/raw.bin').read_bytes() == d[2]
    assert not (tmp_path/'science/terminal.json').exists()


@pytest.mark.parametrize('filename', ['numerical.bin', 'mapping.bin', 'result.bin'])
@pytest.mark.parametrize('after_write', [False, True])
def test_output_write_failure_retains_prefix_and_cannot_retry(tmp_path, saved, monkeypatch, filename, after_write):
    d = durable_source(tmp_path, saved)
    original = api.io.write_new
    def fail(path, raw):
        if path.name == filename:
            if after_write: original(path, raw)
            raise OSError('injected output confirmation failure')
        return original(path, raw)
    monkeypatch.setattr(api.io, 'write_new', fail)
    with pytest.raises(OSError): consume(tmp_path, d)
    names = ['numerical.bin', 'mapping.bin', 'result.bin']
    for pos, name in enumerate(names):
        assert (tmp_path/'science'/name).exists() == (pos < names.index(filename) or (name == filename and after_write))
    assert (tmp_path/'science/postsolve_receipt.json').exists()
    assert (d[0].raw.root/'000/raw.bin').read_bytes() == d[2]
    assert not (tmp_path/'science/terminal.json').exists()
    with pytest.raises(FileExistsError): consume(tmp_path, d)


def test_terminal_written_but_confirmation_failed_returns_no_pin(tmp_path, saved, monkeypatch):
    d = durable_source(tmp_path, saved)
    original = api.io.write_metadata
    def fail(path, doc):
        pin = original(path, doc)
        if path.name == 'terminal.json': raise OSError('terminal confirmation failed')
        return pin
    monkeypatch.setattr(api.io, 'write_metadata', fail)
    returned = []
    with pytest.raises(OSError): returned.append(consume(tmp_path, d))
    assert returned == []
    assert (tmp_path/'science/terminal.json').exists()
    assert not d[0].complete
    assert not (d[0].root/'complete.json').exists()
    assert (d[0].raw.root/'000/raw.bin').read_bytes() == d[2]
    with pytest.raises(FileExistsError): consume(tmp_path, d)


@pytest.mark.parametrize('phase', ['consume', 'inspect'])
def test_producer_source_mutation_during_science_is_rejected(tmp_path, saved, monkeypatch, phase):
    import os
    d = durable_source(tmp_path, saved)
    result = consume(tmp_path, d) if phase == 'inspect' else None
    original = api.audit_stage
    def mutate(*args, **kwargs):
        answer = original(*args, **kwargs)
        path = d[0].root/'binding.json'
        stamp = path.stat()
        raw = path.read_bytes()
        path.write_bytes(raw.replace(b'false', b' true', 1))
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        return answer
    monkeypatch.setattr(api, 'audit_stage', mutate)
    with pytest.raises(ValueError):
        if phase == 'consume': consume(tmp_path, d)
        else: api.inspect(tmp_path/'science', d[5], spec(), LIMITS, 0, d[6], expected_terminal_sha=result['terminal_sha256'])
    if phase == 'consume': assert not (tmp_path/'science/terminal.json').exists()
    assert (d[0].raw.root/'000/raw.bin').read_bytes() == d[2]


def test_wrong_producer_request_is_not_accepted_as_same_model(tmp_path, saved):
    d = durable_source(tmp_path, saved, key_override='f'*64)
    with pytest.raises(ValueError): consume(tmp_path, d)
    assert not (tmp_path/'science').exists()


@pytest.mark.parametrize('fault', [None, 'negative_zero', 'fixed_delta', 'missing_decision'])
def test_completion_eligibility_and_exact_bits(fault):
    from pyomo.environ import ConcreteModel, Var, Binary, Objective
    model = ConcreteModel()
    model.x = Var(domain=Binary)
    model.y = Var()
    model.z = Var(initialize=2.); model.z.fix()
    model.obj = Objective(expr=model.x)
    results = SolverResults()
    results.solver.status = SolverStatus.ok
    results.solver.termination_condition = TerminationCondition.optimal
    results.problem.sense = ProblemSense.minimize
    results.problem.lower_bound = results.problem.upper_bound = 1.
    solution = results.solution.add(); solution.status = SolutionStatus.optimal; solution._cuid = False
    if fault != 'missing_decision': solution.variable['x'] = {'Value': 1.}
    if fault == 'missing_decision':
        with pytest.raises(ValueError, match='missing native decision'):
            api.capture_postsolve(model, results, native_sha='a'*64, key='b'*64)
        return
    post = api.capture_postsolve(model, results, native_sha='a'*64, key='b'*64)
    assert json.loads(post)['completions'] == [
        ['y', (0.).hex(), 'unused_unbounded_continuous_representative'],
        ['z', (2.).hex(), 'canonical_fixed_constant']]
    assignment = dict(x=1., y=-0. if fault == 'negative_zero' else 0., z=2.+1e-10 if fault == 'fixed_delta' else 2.)
    if fault is None: api._postsolve(post, model, assignment, key='b'*64, native_sha='a'*64)
    else:
        with pytest.raises(ValueError, match='assignment differ'):
            api._postsolve(post, model, assignment, key='b'*64, native_sha='a'*64)


@pytest.fixture(scope='module')
def pinned_origin():
    from tests.test_h1_native_export_guard_development_v1 import saved_origin
    return saved_origin.__wrapped__()


@pytest.mark.parametrize('index', [0, 1, 231])
def test_pinned_origin_derived_capsules_match_v3(pinned_origin, index):
    _, p, reports = pinned_origin
    locks = tuple(float.fromhex(meta['lock_hex']) for meta, _ in reports[:index])
    model = model_for(p, index, locks)
    raw, results = synthetic_channels(model, json.loads(reports[index][1]), 'a'*64, 'b'*64)
    # Keep the saved origin's declared time limit.
    report = json.loads(reports[index][1])
    from dataclasses import replace
    specification = replace(spec(), time_limit_seconds=report['solver_options']['TimeLimit'])
    key = api.request_key(p, specification, LIMITS, index, locks)
    post = api.capture_postsolve(model, results, native_sha=api.io.digest(raw), key=key)
    result = api.audit_stage(raw, post, p, specification, LIMITS, index, locks,
        expected_key=key, expected_binding='a'*64, expected_export='b'*64)
    old = api.prior._audit_stage(p, specification, LIMITS, index, locks, reports[index][1])
    assert result['lock'].hex() == old['lock'].hex()
    assert result['assignment'] == old['assignment']
    assert result['generation_mapping'] == old['generation_mapping']


def test_synthetic_tiny_negative_generation_keeps_raw_and_approved_mapping(pinned_origin):
    _, p, reports = pinned_origin
    model = model_for(p, 0, ())
    report = json.loads(reports[0][1])
    chosen = next(n for n, x in report['assignment'] if n.startswith('generation[') and float.fromhex(x) == 0.)
    for row in report['assignment']:
        if row[0] == chosen: row[1] = (-1e-12).hex()
    raw, results = synthetic_channels(model, report, 'a'*64, 'b'*64)
    key = api.request_key(p, spec(), LIMITS, 0, ())
    post = api.capture_postsolve(model, results, native_sha=api.io.digest(raw), key=key)
    result = api.audit_stage(raw, post, p, spec(), LIMITS, 0, (),
        expected_key=key, expected_binding='a'*64, expected_export='b'*64)
    assert dict(result['numerical']['assignment'])[chosen] == (-1e-12).hex()
    assert result['assignment'][chosen] == 0.
    assert any(row[0] == chosen and row[1] == (-1e-12).hex() for row in result['generation_mapping']['changes'])


def test_three_stage_capture_consumer_composition_uses_owned_locks(tmp_path, saved, monkeypatch):
    from tests.test_h1_native_raw_capture_development_v1 import FakeDirect
    from tests.test_h1_linear_export_guard_development_v1 import Native, Handle
    from pyomo.environ import Constraint, Var, Objective
    from pyomo.repn import generate_standard_repn
    class H1FakeDirect(FakeDirect):
        def _postsolve(self):
            super()._postsolve()
            return self.result
    monkeypatch.setattr(api.capture, 'GurobiDirect', H1FakeDirect)
    p, locks = packet(), ()
    for index, old_raw in enumerate(saved[1]):
        model = model_for(p, index, locks)
        report = json.loads(old_raw)
        _, results = synthetic_channels(model, report, 'a'*64, 'b'*64)
        assignments = {n: float.fromhex(x) for n, x in report['assignment']}
        native, identity, cidentity = Native(), object(), object()
        variables = tuple(model.component_data_objects(Var))
        constraints = tuple(model.component_data_objects(Constraint, active=True))
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
            setattr(native, n, float.fromhex(report['provenance']['native'][n]['hex']))
        native.update = lambda: None
        vf, cf = tuple(zip(variables, native.variables)), tuple(zip(constraints, native.constraints))
        args = dict(variable_forward=vf, variable_reverse=tuple((h, v) for v, h in vf),
                    constraint_forward=cf, constraint_reverse=tuple((h, c) for c, h in cf))
        key = api.request_key(p, spec(), LIMITS, index, locks)
        owner = api.capture.StageCapture(tmp_path/f'stage{index}', request_sha256=key,
            expected_structure=api.capture.old.audit._structure(model), expected_implementation=api.capture.implementation_identity())
        solver = H1FakeDirect(model, native, args, owner.root, None)
        solver.result = results
        monkeypatch.setattr(api.capture.old.provenance.adapter, 'create_solver',
            lambda specification: (solver, api.capture.old.audit.solver_options(specification)))
        def callback(raw, result, actual_model):
            return api.consume(owner.root/'science', owner.raw.root/'000/raw.bin', result, actual_model,
                p, spec(), LIMITS, index, locks, expected_native_sha=api.io.digest(raw),
                expected_binding=owner.binding_sha, expected_export=owner.records['export.json'])
        result = owner.run(lambda: model, spec(), callback)
        assert owner.complete and solver.apply_calls == solver.close_calls == 1
        locks = (*locks, result['result']['lock'])
        assert not result['stage_capture_completion_checked']
    assert locks == (20., 1., 20.)


def test_mid_replay_mutation_rejected_even_with_restored_mtime(tmp_path, saved, monkeypatch):
    import os
    d = durable_source(tmp_path, saved); result = consume(tmp_path, d)
    path = tmp_path/'science/numerical.bin'
    original = api.audit_stage
    def mutate(*args, **kwargs):
        computed = original(*args, **kwargs)
        info = path.stat()
        old = path.read_bytes()
        altered = old.replace(b'derived_legacy_predicate_view', b'corrupt_legacy_predicate_view')
        assert len(altered) == len(old) and altered != old
        path.write_bytes(altered)
        os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))
        return computed
    monkeypatch.setattr(api, 'audit_stage', mutate)
    with pytest.raises(ValueError, match='changed during replay'):
        api.inspect(tmp_path/'science', d[5], spec(), LIMITS, 0, d[6], expected_terminal_sha=result['terminal_sha256'])
