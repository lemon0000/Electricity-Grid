"""Zero-solver scientific consumer for the new retained native capsule.

All results are conditional on supplied immutable views. No native execution,
capture completion, source-parent completion or formal acceptance is inferred.
"""
from fractions import Fraction
from dataclasses import asdict
import math
from pathlib import Path
import re
import struct

from pyomo.environ import Constraint, Objective, Var, value
from pyomo.opt import SolverResults, SolverStatus, TerminationCondition, SolutionStatus, ProblemSense
from pyomo.repn import generate_standard_repn

from experiments import h1_native_raw_capture_development_v1 as capture
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_hour_replay_v3 as prior

io = capture.io
SCHEMA = 'h1_native_raw_science_development_v1'
POST_CAP = 256 * 1024


def implementation_identity():
    return io.digest(io.encode(dict(schema=SCHEMA, capture=capture.implementation_identity(),
        scientific_replay=prior.implementation_identity(), files={Path(m.__file__).name:
        io.digest(Path(m.__file__).read_bytes()) for m in
        (prior.native.predicate, prior.native.replay, prior.native.replay.entry)},
        own=io.digest(Path(__file__).read_bytes()))))


def _keys(item, names):
    if type(item) is not dict or set(item) != set(names):
        raise ValueError('exact record fields required')


def _hex(text):
    if type(text) is not str:
        raise ValueError('canonical finite binary64 hex required')
    number = float.fromhex(text)
    if not math.isfinite(number) or number.hex() != text:
        raise ValueError('canonical finite binary64 hex required')
    return number


def _atom(atom, kind):
    _keys(atom, ('kind', 'value', 'bits') if kind == 'binary64' else ('kind', 'value'))
    if atom['kind'] != kind:
        raise ValueError('native atom kind differs')
    item = atom['value']
    if kind == 'binary64':
        if type(atom['bits']) is not str or re.fullmatch('[0-9a-f]{16}', atom['bits']) is None:
            raise ValueError('exact binary64 bits required')
        number = struct.unpack('>d', bytes.fromhex(atom['bits']))[0]
        if type(item) is not str or number.hex() != item or not math.isfinite(number):
            raise ValueError('native bits/hex differ or nonfinite output')
        return number
    if type(item) is not (int if kind == 'integer' else str):
        raise ValueError('native atom type differs')
    return item


def _channel(channel, kind, *, optional=False):
    _keys(channel, ('available', 'atom', 'error'))
    if channel['available'] is False:
        if (not optional or channel['atom'] is not None or type(channel['error']) is not str
                or not 1 <= len(channel['error']) <= 64):
            raise ValueError('required native channel unavailable')
        return None
    if channel['available'] is not True or channel['error'] is not None:
        raise ValueError('native channel state differs')
    return _atom(channel['atom'], kind)


def decode_native(raw, model, *, expected_binding, expected_export):
    for pin in (expected_binding, expected_export): io.pin(pin)
    doc = prior.old._decode(raw, io.RAW_CAP)
    _keys(doc, ('schema', 'binding_sha256', 'export_sha256', 'apply_error', 'attributes',
                'variables', 'objective', 'values_transformed', *capture.FLAGS))
    if (doc['schema'] != capture.SCHEMA or doc['binding_sha256'] != expected_binding
            or doc['export_sha256'] != expected_export or doc['apply_error'] is not None
            or doc['values_transformed'] is not False or any(doc[k] is not False for k in capture.FLAGS)):
        raise ValueError('native capsule binding or scope differs')
    variables, count, constant, coefficients = capture.export._canonical(model)
    canonical = {v.name: v for v in variables}
    _keys(doc['attributes'], capture.ATTRIBUTES)
    integer_names = ('Status', 'SolCount', 'ModelSense', 'NumVars', 'NumConstrs')
    attrs = {name: _channel(channel, 'integer' if name in integer_names else 'binary64',
                            optional=name == 'MIPGap') for name, channel in doc['attributes'].items()}
    if attrs['NumVars'] != len(variables) or attrs['NumConstrs'] != count or attrs['ModelSense'] != 1:
        raise ValueError('native capsule model shape differs')
    rows = doc['variables']
    if type(rows) is not list or len(rows) != len(variables):
        raise ValueError('complete native variable inventory required')
    assignment, indices = {}, {}
    for row in rows:
        _keys(row, ('canonical_name', 'attributes'))
        name = row['canonical_name']
        if type(name) is not str or name not in canonical or name in assignment:
            raise ValueError('duplicate or foreign canonical variable')
        _keys(row['attributes'], ('index', 'VarName', 'VType', 'LB', 'UB', 'X'))
        values = {key: _channel(ch, 'integer' if key == 'index' else 'string' if key in ('VarName', 'VType')
                               else 'binary64') for key, ch in row['attributes'].items()}
        index = values['index']
        if not 0 <= index < len(variables) or index in indices:
            raise ValueError('native variable index inventory differs')
        indices[index] = name
        var = canonical[name]
        kind = 'B' if var.is_binary() else 'I' if var.is_integer() else 'C' if var.is_continuous() else None
        if kind is None or values['VType'] != kind:
            raise ValueError('native variable domain differs')
        for side, bound, infinity in (('LB', var.value if var.fixed else var.lb, -1e100),
                                      ('UB', var.value if var.fixed else var.ub, 1e100)):
            expected = infinity if bound is None else float(value(bound))
            if bound is not None and (not math.isfinite(expected) or abs(expected) >= 1e20):
                raise ValueError('canonical bound outside strict native envelope')
            if values[side].hex() != expected.hex():
                raise ValueError('native variable bound differs')
        if var.fixed and values['X'].hex() != float(value(var)).hex():
            raise ValueError('fixed native assignment differs')
        assignment[name] = values['X']
    objective = doc['objective']
    _keys(objective, ('constant', 'count', 'terms', 'error'))
    n = _atom(objective['count'], 'integer')
    if objective['error'] is not None or not 0 <= n <= 362 or type(objective['terms']) is not list or len(objective['terms']) != n:
        raise ValueError('complete bounded native objective required')
    native_constant = _channel(objective['constant'], 'binary64')
    terms, actual = [], {}
    for row in objective['terms']:
        _keys(row, ('index', 'coefficient'))
        index, coef = _channel(row['index'], 'integer'), _channel(row['coefficient'], 'binary64')
        if index not in indices or indices[index] in actual:
            raise ValueError('foreign or duplicate native objective term')
        name = indices[index]
        actual[name] = Fraction.from_float(coef)
        terms.append([name, coef.hex(), assignment[name].hex()])
    if Fraction.from_float(native_constant) != constant or {n: c for n, c in actual.items() if c} != coefficients:
        raise ValueError('native objective algebra differs from canonical model')
    return assignment, attrs, native_constant, terms


def request_key(packet, specification, limits, index, locks):
    base = prior.request_key(packet, specification, limits)
    order = prior.native.model_api.stage_order(packet.inputs)
    if type(index) is not int or not 0 <= index < len(order) or type(locks) is not tuple or len(locks) != index:
        raise ValueError('exact stage and complete lock prefix required')
    request = prior.native.model_api.H1StageRequest(packet.inputs, locks)
    return io.digest(io.encode([SCHEMA, implementation_identity(), base, index,
                               prior.native.model_api.h1_stage_identity(request)]))


def capture_postsolve(model, results, *, native_sha, key):
    """Extract through existing validated APIs; native raw is already durable.

    Extraction failure leaves native raw intact; it does not promise complete
    Pyomo output retention. This function neither loads nor audits assignments.
    """
    for pin in (native_sha, key): io.pin(pin)
    if type(results) is not SolverResults or len(results.solver) != 1 or len(results.problem) != 1 or len(results.solution) != 1:
        raise ValueError('exact single Pyomo result required')
    s, p, x = results.solver[0], results.problem[0], results.solution[0]
    if (type(s.status) is not SolverStatus or type(s.termination_condition) is not TerminationCondition
            or type(x.status) is not SolutionStatus or p.sense is not ProblemSense.minimize):
        raise ValueError('typed minimization result channels required')
    values = capture.old.audit._native_values(model, results, 'variable', Var)
    completed = capture.old.audit._canonical_completions(model, values)
    return io.encode(dict(schema=SCHEMA+'_pyomo', key=key, native_sha256=native_sha,
        status=str(s.status), termination=str(s.termination_condition), solution_status=str(x.status),
        sense=str(p.sense), solver_records=1, problem_records=1, solution_records=1,
        lower=float(p.lower_bound).hex(), upper=float(p.upper_bound).hex(),
        reported_values=[[n, float(v).hex()] for n, v in values],
        completions=[[n, float(v).hex(), reason] for n, v, reason in completed]))


def _postsolve(raw, model, assignment, *, key, native_sha):
    doc = prior.old._decode(raw, POST_CAP)
    _keys(doc, ('schema', 'key', 'native_sha256', 'status', 'termination', 'solution_status',
                'sense', 'solver_records', 'problem_records', 'solution_records',
                'lower', 'upper', 'reported_values', 'completions'))
    if doc['schema'] != SCHEMA+'_pyomo' or doc['key'] != key or doc['native_sha256'] != native_sha:
        raise ValueError('Pyomo sidecar binding differs')
    if doc['sense'] != 'minimize' or any(type(doc[n]) is not int or doc[n] != 1
        for n in ('solver_records', 'problem_records', 'solution_records')):
        raise ValueError('single minimization sidecar required')
    for name in ('status', 'termination', 'solution_status'):
        if type(doc[name]) is not str or len(doc[name]) > 64: raise ValueError('bounded status required')
    _hex(doc['lower']); _hex(doc['upper'])
    rows = doc['reported_values']
    if (type(rows) is not list or len(rows) > len(assignment)
            or any(type(r) is not list or len(r) != 2 or type(r[0]) is not str for r in rows)):
        raise ValueError('bounded Pyomo assignment rows required')
    values = tuple((n, _hex(v)) for n, v in rows)
    if len(dict(values)) != len(values) or list(rows) != sorted(rows) or set(dict(values)) - set(assignment):
        raise ValueError('Pyomo assignment inventory differs')
    completed = capture.old.audit._canonical_completions(model, values)
    if doc['completions'] != [[n, float(v).hex(), reason] for n, v, reason in completed]:
        raise ValueError('canonical completion rule differs')
    combined = dict(values + tuple((n, v) for n, v, _ in completed))
    if set(combined) != set(assignment) or any(struct.pack('>d', combined[n]) != struct.pack('>d', assignment[n]) for n in assignment):
        raise ValueError('native X and Pyomo/completed assignment differ')
    return doc


def _numerical(model, specification, assignment, attrs, native_constant, native_terms, post):
    structure = capture.old.audit._structure(model)
    for variable in model.component_data_objects(Var):
        variable.set_value(assignment[variable.name], skip_validation=True)
    residual = capture.old.audit._constraint_violation(model)
    integer = capture.old.audit._integrality_violation(model)
    expr = next(model.component_data_objects(Objective, active=True)).expr
    repn = generate_standard_repn(expr, compute_values=True)
    terms = [[v.name, float(c).hex(), assignment[v.name].hex()]
             for v, c in zip(repn.linear_vars, repn.linear_coefs, strict=True)]
    constant = float(value(repn.constant))
    canonical = float(value(expr))
    refs = {v.name for v in repn.linear_vars}
    for row in model.component_data_objects(Constraint, active=True):
        refs.update(v.name for v in generate_standard_repn(row.body, compute_values=True).linear_vars)
    referenced = sorted([n, assignment[n].hex()] for n in refs)
    provenance = capture.old.provenance
    def exact(c, rows):
        total = Fraction.from_float(c) + sum((Fraction.from_float(float.fromhex(coef)) *
            Fraction.from_float(float.fromhex(x)) for _, coef, x in rows), Fraction(0))
        return dict(numerator=str(total.numerator), denominator=str(total.denominator))
    canonical_exact, native_exact = exact(constant, terms), exact(native_constant, native_terms)
    canonical_algebra, native_algebra = provenance._algebra(constant, terms), provenance._algebra(native_constant, native_terms)
    p = dict(schema='rq2_objective_provenance_v1', collector_sha256=io.digest(Path(__file__).read_bytes()),
        adapter_identity=provenance.adapter.implementation_identity(),
        native={n: dict(available=True, hex=attrs[n].hex(), error=None) for n in ('ObjVal', 'ObjBound', 'ObjBoundC', 'Runtime')},
        native_status=attrs['Status'], native_solution_count=attrs['SolCount'], native_model_sense=attrs['ModelSense'],
        is_mip=any(v.is_integer() for v in model.component_data_objects(Var)),
        pyomo_status=post['status'], pyomo_termination=post['termination'], pyomo_solution_status=post['solution_status'],
        pyomo_lower_hex=post['lower'], pyomo_upper_hex=post['upper'], canonical_objective_hex=canonical.hex(),
        constant_hex=constant.hex(), native_constant_hex=native_constant.hex(), ordered_objective_terms=terms,
        ordered_native_objective_terms=native_terms, exact_objective=canonical_exact, native_exact_objective=native_exact,
        canonical_objective_algebra=canonical_algebra, native_objective_algebra=native_algebra,
        native_algebra_equals_canonical_algebra=native_algebra == canonical_algebra,
        native_exact_value_equals_canonical_exact_value=native_exact == canonical_exact,
        referenced_assignment=referenced, assignment_sha256=io.digest(repr(tuple(tuple(r) for r in referenced)).encode()),
        comparisons=provenance.compare_channels(native_objective=attrs['ObjVal'], native_bound=attrs['ObjBound'],
            pyomo_lower=_hex(post['lower']), pyomo_upper=_hex(post['upper']), canonical_objective=canonical,
            exact_objective=Fraction(int(canonical_exact['numerator']), int(canonical_exact['denominator']))))
    return dict(schema=SCHEMA+'_numerical', evidence_role='derived_legacy_predicate_view',
        implementation_identity=implementation_identity(),
        model_structure_identity=structure, variables=len(assignment), assignment=sorted([n, x.hex()] for n, x in assignment.items()),
        provenance=p, maximum_residual=residual, maximum_integrality_violation=integer,
        assignment_valid=bool(residual <= specification.feasibility_tolerance and integer <= specification.integer_feasibility_tolerance),
        solver_calls_by_consumer=0, **capture.FLAGS)


def audit_stage(native_raw, postsolve_raw, packet, specification, limits, index, locks, *,
                expected_key, expected_binding, expected_export):
    """Independent build, unchanged numeric predicate, approved projection.

    Does not authenticate StageCapture completion or native execution. On a
    projection rejection its existing error.receipt must be retained by caller.
    """
    with prior.guard.solver_calls_forbidden():
        if request_key(packet, specification, limits, index, locks) != expected_key:
            raise ValueError('scientific stage key differs')
        own = implementation_identity()
        model_api = prior.native.model_api
        request = model_api.H1StageRequest(packet.inputs, locks)
        stage_pin = model_api.h1_stage_identity(request)
        model = model_api.build_h1_stage_model(request, expected_identity=stage_pin)
        scale = capture.old.audit.model_scale(model)
        if scale.variables > limits.max_variables or scale.constraints > limits.max_constraints:
            raise ValueError('scientific stage exceeds declared shape')
        fresh, projection_model = model.clone(), model.clone()
        assignment, attrs, constant, terms = decode_native(native_raw, model,
            expected_binding=expected_binding, expected_export=expected_export)
        post = _postsolve(postsolve_raw, model, assignment, key=expected_key, native_sha=io.digest(native_raw))
        numerical = _numerical(model, specification, assignment, attrs, constant, terms, post)
        prior.native.replay.verify_numerical(fresh, numerical)
        numeric = prior.native.predicate.evaluate(numerical, expected_implementation=own,
            expected_collector=io.digest(Path(__file__).read_bytes()),
            expected_adapter=capture.old.provenance.adapter.implementation_identity())
        if not numeric['candidate_numeric_predicate_passed']:
            raise ValueError('unchanged numerical predicate rejected')
        candidate, audit, mapping = prior.generation_projection._project_and_audit_built(
            request, assignment, projection_model, expected_identity=stage_pin,
            raw_objective_hex=numerical['provenance']['canonical_objective_hex'])
        lock = audit.canonical_objective
        if model_api.stage_order(packet.inputs)[index][0] == 'commitment':
            rounded = float(round(lock))
            if rounded not in (0., 1.) or abs(rounded-lock) > 1e-9:
                raise ValueError('commitment objective is not audited binary')
            lock = rounded
        if implementation_identity() != own or request_key(packet, specification, limits, index, locks) != expected_key:
            raise ValueError('scientific dependency/input drift')
        return dict(lock=lock, assignment=candidate, generation_mapping=mapping, numerical=numerical,
            numeric=numeric, stage_identity=stage_pin, native_sha256=io.digest(native_raw),
            postsolve_sha256=io.digest(postsolve_raw), stage_capture_completion_checked=False, **capture.FLAGS)


def _outputs(result):
    numerical = io.encode(result['numerical'])
    mapping = io.encode(result['generation_mapping'])
    payload = io.encode(dict(schema=SCHEMA+'_result', lock_hex=result['lock'].hex(),
        assignment=sorted([n, v.hex()] for n, v in result['assignment'].items()),
        stage_identity=result['stage_identity'], native_sha256=result['native_sha256'],
        postsolve_sha256=result['postsolve_sha256'], numerical_sha256=io.digest(numerical),
        mapping_sha256=io.digest(mapping), numeric=result['numeric'],
        stage_capture_completion_checked=False, **capture.FLAGS))
    return {'numerical.bin': numerical, 'mapping.bin': mapping, 'result.bin': payload}


def _source_view(native_path, key, model, specification, expected_binding, expected_export):
    """Bind science request to the pending producer's actual saved source chain."""
    if native_path.name != 'raw.bin' or native_path.parent.name != '000' or native_path.parent.parent.name != 'native_raw':
        raise ValueError('exact single-stage capture source path required')
    root = native_path.parent.parent.parent
    names = ('binding.json', 'specification.json', 'export.json', 'native_raw/binding.json',
             'native_raw/000/intent.json', 'native_raw/000/raw_receipt.json', 'native_raw/000/outcome.json')
    views = {name: io.read_stable(root/name, io.META_CAP) for name in names}
    raw, raw_stamp = io.read_stable(native_path, io.RAW_CAP)
    digests = {name: io.digest(data) for name, (data, _) in views.items()}
    structure = capture.old.audit._structure(model)
    expected = {
        'binding.json': dict(schema=capture.SCHEMA, request_sha256=key, expected_structure=structure,
            implementation=capture.implementation_identity(), **capture.FLAGS),
        'specification.json': dict(specification=asdict(specification),
            options=capture.old.audit.solver_options(specification), binding_sha256=expected_binding),
        'native_raw/binding.json': dict(schema=io.SCHEMA, request_sha256=key, stages=1,
            raw_cap=io.RAW_CAP, meta_cap=io.META_CAP),
        'native_raw/000/intent.json': dict(schema=io.SCHEMA, stage=0, request_sha256=key,
            previous=digests['native_raw/binding.json']),
        'native_raw/000/raw_receipt.json': dict(schema=io.SCHEMA, stage=0,
            intent_sha256=digests['native_raw/000/intent.json'], raw_sha256=io.digest(raw), raw_bytes=len(raw)),
        'native_raw/000/outcome.json': dict(schema=io.SCHEMA, stage=0,
            raw_receipt_sha256=digests['native_raw/000/raw_receipt.json'], state='consumer_returned')}
    variables, count, _, _ = capture.export._canonical(model)
    expected['export.json'] = dict(binding_sha256=expected_binding,
        specification_sha256=digests['specification.json'], model_structure=structure,
        result=dict(schema='h1_linear_export_guard_development_v1', variables=len(variables), constraints=count,
            exact_linear_correspondence_checked=True, native_export_coverage=False,
            native_execution_authenticated=False, resource_admission=False, formal_execution_ready=False, formal_result=False))
    if digests['binding.json'] != expected_binding or digests['export.json'] != expected_export:
        raise ValueError('external producer binding/export pin differs')
    if any(io.encode(expected[name]) != views[name][0] for name in names):
        raise ValueError('producer request/specification/raw chain differs')
    if any(io.identity(root/name) != stamp for name, (_, stamp) in views.items()) or io.identity(native_path) != raw_stamp:
        raise ValueError('producer source view changed')
    return io.digest(io.encode(digests)), tuple((root/name, stamp, raw) for name, (raw, stamp) in views.items())


def consume(root, native_path, results, model, packet, specification, limits, index, locks, *,
            expected_native_sha, expected_binding, expected_export):
    """Create-once sidecar and scientific artifacts, then fresh independent replay.

    Intended as StageCapture's callback. It grants no run authority. Its terminal
    proves science views only: later producer close/finish may still fail.
    """
    with prior.guard.solver_calls_forbidden():
        root, native_path = Path(root).resolve(), Path(native_path).resolve()
        for pin in (expected_native_sha, expected_binding, expected_export): io.pin(pin)
        key = request_key(packet, specification, limits, index, locks)
        native_raw, stamp = io.read_stable(native_path, io.RAW_CAP)
        if io.digest(native_raw) != expected_native_sha or len(str(native_path)) > 1024:
            raise ValueError('native source pin/path differs')
        req = prior.native.model_api.H1StageRequest(packet.inputs, locks)
        canonical = prior.native.model_api.build_h1_stage_model(req,
            expected_identity=prior.native.model_api.h1_stage_identity(req))
        structure = capture.old.audit._structure(canonical)
        if capture.old.audit._structure(model) != structure:
            raise ValueError('callback model structure differs')
        source_pin, source_stamps = _source_view(native_path, key, canonical, specification, expected_binding, expected_export)
        decode_native(native_raw, canonical, expected_binding=expected_binding, expected_export=expected_export)
        root.mkdir(exist_ok=False)
        intent = dict(schema=SCHEMA, key=key, native_path=str(native_path), native_sha256=expected_native_sha,
            binding_sha256=expected_binding, export_sha256=expected_export, model_structure=structure,
            implementation=implementation_identity(), capture_source_sha256=source_pin)
        intent_sha = io.write_metadata(root/'intent.json', intent)
        post = capture_postsolve(model, results, native_sha=expected_native_sha, key=key)
        if len(post) > POST_CAP: raise ValueError('postsolve sidecar exceeds cap')
        io.write_new(root/'postsolve.bin', post)
        receipt = dict(schema=SCHEMA, intent_sha256=intent_sha, postsolve_sha256=io.digest(post),
                       postsolve_bytes=len(post), native_sha256=expected_native_sha)
        receipt_sha = io.write_metadata(root/'postsolve_receipt.json', receipt)
        fresh = io.read_stable(root/'postsolve.bin', POST_CAP)[0]
        if fresh != post: raise ValueError('sidecar changed before science')
        try:
            result = audit_stage(native_raw, fresh, packet, specification, limits, index, locks,
                expected_key=key, expected_binding=expected_binding, expected_export=expected_export)
        except prior.generation_projection.ProjectionRejected as error:
            rejected_mapping = io.encode(error.receipt)
            if len(rejected_mapping) > POST_CAP: raise ValueError('rejected mapping exceeds cap') from error
            io.write_new(root/'mapping.bin', rejected_mapping)
            raise
        outputs = _outputs(result)
        for name, raw in outputs.items():
            if len(raw) > (io.RAW_CAP if name == 'numerical.bin' else POST_CAP):
                raise ValueError('scientific artifact exceeds cap')
            io.write_new(root/name, raw)
        if (io.identity(native_path) != stamp or io.read_stable(native_path, io.RAW_CAP)[0] != native_raw
                or any(io.read_stable(path, io.META_CAP) != (data, before) for path, before, data in source_stamps)):
            raise ValueError('native source changed during science')
        terminal = dict(schema=SCHEMA, key=key, intent_sha256=intent_sha, receipt_sha256=receipt_sha,
            files_sha256={name: io.digest(raw) for name, raw in outputs.items()},
            native_sha256=expected_native_sha, postsolve_sha256=io.digest(post),
            stage_capture_completion_checked=False, **capture.FLAGS)
        terminal_sha = io.write_metadata(root/'terminal.json', terminal)
        replayed = inspect(root, packet, specification, limits, index, locks, expected_terminal_sha=terminal_sha)
        return dict(result=replayed, terminal_sha256=terminal_sha,
                    stage_capture_completion_checked=False, **capture.FLAGS)


def inspect(root, packet, specification, limits, index, locks, *, expected_terminal_sha):
    """Fresh science replay only; external StageCapture completion still needed."""
    with prior.guard.solver_calls_forbidden():
        io.pin(expected_terminal_sha)
        root = Path(root).resolve()
        allowed = {'intent.json', 'postsolve.bin', 'postsolve_receipt.json', 'numerical.bin',
                   'mapping.bin', 'result.bin', 'terminal.json'}
        if {p.name for p in root.iterdir()} != allowed: raise ValueError('science topology differs')
        views = {}
        for name in allowed:
            cap = io.RAW_CAP if name == 'numerical.bin' else POST_CAP if name.endswith('.bin') else io.META_CAP
            views[name] = io.read_stable(root/name, cap)
        terminal = prior.old._decode(views['terminal.json'][0], io.META_CAP)
        if io.digest(views['terminal.json'][0]) != expected_terminal_sha:
            raise ValueError('external science terminal pin differs')
        intent = prior.old._decode(views['intent.json'][0], io.META_CAP)
        _keys(intent, ('schema', 'key', 'native_path', 'native_sha256', 'binding_sha256',
                       'export_sha256', 'model_structure', 'implementation', 'capture_source_sha256'))
        key = request_key(packet, specification, limits, index, locks)
        if intent['schema'] != SCHEMA or intent['key'] != key or intent['implementation'] != implementation_identity():
            raise ValueError('scientific request/implementation differs')
        native_path = Path(intent['native_path'])
        if str(native_path.resolve()) != str(native_path) or len(str(native_path)) > 1024:
            raise ValueError('canonical absolute native path required')
        native, stamp = io.read_stable(native_path, io.RAW_CAP)
        if io.digest(native) != intent['native_sha256']: raise ValueError('native pin differs')
        post = views['postsolve.bin'][0]
        req = prior.native.model_api.H1StageRequest(packet.inputs, locks)
        model = prior.native.model_api.build_h1_stage_model(req,
            expected_identity=prior.native.model_api.h1_stage_identity(req))
        source_pin, source_stamps = _source_view(native_path, key, model, specification,
                                               intent['binding_sha256'], intent['export_sha256'])
        if source_pin != intent['capture_source_sha256']: raise ValueError('producer source pin differs')
        receipt = dict(schema=SCHEMA, intent_sha256=io.digest(views['intent.json'][0]),
            postsolve_sha256=io.digest(post), postsolve_bytes=len(post), native_sha256=io.digest(native))
        if io.encode(receipt) != views['postsolve_receipt.json'][0]: raise ValueError('sidecar receipt differs')
        result = audit_stage(native, post, packet, specification, limits, index, locks,
            expected_key=key, expected_binding=intent['binding_sha256'], expected_export=intent['export_sha256'])
        if result['numerical']['model_structure_identity'] != intent['model_structure']:
            raise ValueError('science model structure differs')
        outputs = _outputs(result)
        if any(raw != views[name][0] for name, raw in outputs.items()):
            raise ValueError('fresh scientific replay differs')
        expected = dict(schema=SCHEMA, key=key, intent_sha256=io.digest(views['intent.json'][0]),
            receipt_sha256=io.digest(views['postsolve_receipt.json'][0]),
            files_sha256={name: io.digest(raw) for name, raw in outputs.items()},
            native_sha256=io.digest(native), postsolve_sha256=io.digest(post),
            stage_capture_completion_checked=False, **capture.FLAGS)
        if not io.same(terminal, expected): raise ValueError('scientific terminal differs')
        if ({p.name for p in root.iterdir()} != allowed or io.read_stable(native_path, io.RAW_CAP) != (native, stamp)
                or any(io.read_stable(path, io.META_CAP) != (data, before) for path, before, data in source_stamps)
                or any(io.read_stable(root/name, len(data)) != (data, info) for name, (data, info) in views.items())):
            raise ValueError('science view changed during replay')
        return result
