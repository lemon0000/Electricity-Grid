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


def durable_source(tmp_path, saved):
    p, locks, model, raw, post, results, key = sample(saved)
    owner = api.capture.StageCapture(tmp_path/'producer', request_sha256=key,
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


def test_wrong_producer_request_is_not_accepted_as_same_model(tmp_path, saved):
    d = durable_source(tmp_path, saved)
    binding = json.loads((d[0].root/'binding.json').read_bytes())
    binding['request_sha256'] = 'f'*64
    (d[0].root/'binding.json').write_bytes(api.io.encode(binding))
    with pytest.raises(ValueError): consume(tmp_path, d)
    assert not (tmp_path/'science').exists()
