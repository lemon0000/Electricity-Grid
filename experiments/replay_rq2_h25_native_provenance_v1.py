"""Independent zero-solver reconstruction of a pinned native H25 diagnostic."""
import argparse
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pyomo.environ import Objective, Var, Constraint, value
from pyomo.repn import generate_standard_repn
from experiments import audit_rq2_h25_native_provenance_v1 as entry


def verify_numerical(model, n):
    """Rebuild arithmetic from canonical model; archived native channel is data."""
    api = entry.run
    p = n['provenance']
    if p is None:
        raise ValueError('native provenance absent; no numeric replay available')
    if api.audit._structure(model) != n['model_structure_identity']:
        raise ValueError('canonical model structure mismatch')
    assignment = dict(n['assignment'])
    variables = {v.name: v for v in model.component_data_objects(Var)}
    if len(n['assignment']) != len(assignment) or set(assignment) != set(variables):
        raise ValueError('complete unique assignment required')
    fixed_valid = True
    for name, variable in variables.items():
        number = float.fromhex(assignment[name])
        if not api.audit.isfinite(number):
            raise ValueError('finite assignment required')
        if variable.fixed and abs(number-variable.value) > 1e-9:
            fixed_valid = False
        variable.set_value(number, skip_validation=True)
    residual, integer = api.audit._constraint_violation(model), api.audit._integrality_violation(model)
    if (residual != n['maximum_residual'] or integer != n['maximum_integrality_violation']
            or bool(fixed_valid and residual <= 1e-9 and integer <= 1e-9) is not n['assignment_valid']):
        raise ValueError('canonical residual or validity flag mismatch')
    expr = next(model.component_data_objects(Objective, active=True)).expr
    repn = generate_standard_repn(expr, compute_values=True)
    if not repn.is_linear():
        raise ValueError('linear objective required')
    terms = [(v.name, float(c).hex(), assignment[v.name])
             for v,c in zip(repn.linear_vars,repn.linear_coefs,strict=True)]
    def exact(constant, terms):
        total=Fraction.from_float(float.fromhex(constant))
        for name,coef,assigned in terms:
            if name not in assignment or assigned != assignment[name]:
                raise ValueError('objective term assignment mismatch')
            total += Fraction.from_float(float.fromhex(coef))*Fraction.from_float(float.fromhex(assigned))
        return {'numerator':str(total.numerator),'denominator':str(total.denominator)}
    native_terms=p['ordered_native_objective_terms']
    canonical_algebra=api.provenance._algebra(float(repn.constant),terms)
    native_algebra=api.provenance._algebra(float.fromhex(p['native_constant_hex']),native_terms)
    computed={
        'canonical_objective_hex':float(value(expr)).hex(),
        'constant_hex':float(repn.constant).hex(), 'ordered_objective_terms':terms,
        'exact_objective':exact(float(repn.constant).hex(),terms),
        'native_exact_objective':exact(p['native_constant_hex'],native_terms),
        'canonical_objective_algebra':canonical_algebra,
        'native_objective_algebra':native_algebra,
        'native_algebra_equals_canonical_algebra':native_algebra==canonical_algebra,
    }
    computed['native_exact_value_equals_canonical_exact_value']=(computed['exact_objective']==computed['native_exact_objective'])
    refs={v.name for v in repn.linear_vars}
    for constraint in model.component_data_objects(Constraint,active=True):
        row=generate_standard_repn(constraint.body,compute_values=True)
        if not row.is_linear():
            raise ValueError('linear constraints required')
        refs.update(v.name for v in row.linear_vars)
    referenced=tuple(sorted((name,assignment[name]) for name in refs))
    computed['referenced_assignment']=referenced
    computed['assignment_sha256']=sha256(repr(referenced).encode()).hexdigest()
    q=computed['exact_objective']
    computed['comparisons']=api.provenance.compare_channels(
        native_objective=float.fromhex(p['native']['ObjVal']['hex']),
        native_bound=float.fromhex(p['native']['ObjBound']['hex']),
        pyomo_lower=float.fromhex(p['pyomo_lower_hex']),pyomo_upper=float.fromhex(p['pyomo_upper_hex']),
        canonical_objective=float(value(expr)),exact_objective=Fraction(int(q['numerator']),int(q['denominator'])))
    for key, expected in computed.items():
        if api.encode(expected) != api.encode(p[key]):
            raise ValueError('provenance recomputation differs: '+key)
    return dict(canonical_assignment_recomputed=True, objective_algebra_recomputed=True,
        objective_channels_recomputed=True, maximum_residual=residual,
        maximum_integrality_violation=integer, solver_calls_by_replay=0,
        native_execution_authenticated=False, normal_accepted=False, formal_result=False)


def replay(expected_result, expected_record):
    root=entry.OUTPUT
    snapshots={name:entry.retained(root/name) for name in
               ('result.json','intent.json','launch.json','observation.json','native_record.json')}
    if snapshots['result.json'][1]!=expected_result or snapshots['native_record.json'][1]!=expected_record:
        raise ValueError('external diagnostic pins differ')
    manifest=json.loads(snapshots['result.json'][2])
    for name,pin in manifest['file_sha256'].items():
        if snapshots[name][1]!=pin:
            raise ValueError('diagnostic manifest file mismatch')
    report=json.loads(snapshots['native_record.json'][2])
    request,identity=entry.check(report['script_sha256'],report['runner_identity'])
    entry.validate_record(report,request,identity,report['script_sha256'],report['runner_identity'])
    source=entry.transport.source
    targets=((entry.run,'solve_once'),(entry.run.provenance.adapter,'create_solver'),
        (source,'run_source'),(source.kernel,'run_normal_only'),(source.kernel.native,'_solve'))
    originals=[(module,name,getattr(module,name)) for module,name in targets]
    def forbidden(*args,**kwargs):
        raise RuntimeError('solver forbidden during independent replay')
    own_pin=sha256(Path(__file__).read_bytes()).hexdigest()
    try:
        for module,name in targets: setattr(module,name,forbidden)
        inputs,_=source._prepare(request,identity)
        stream=source.kernel.streaming
        model=stream.build_continuous_normal_model(inputs,expected_identity=request.source.expected_input_identity,
            expected_implementation_identity=stream.implementation_identity())
        numerical=verify_numerical(model,report['numerical'])
        if entry.check(report['script_sha256'],report['runner_identity'])[1]!=identity:
            raise ValueError('source drift during replay')
        for name,before in snapshots.items():
            if entry.retained(root/name)!=before:
                raise ValueError('diagnostic evidence changed during replay')
        if sha256(Path(__file__).read_bytes()).hexdigest()!=own_pin:
            raise ValueError('replay implementation drift')
        return dict(schema='rq2_h25_native_provenance_replay_v1', result_sha256=expected_result,
            record_sha256=expected_record,source_request_identity=identity,generator_sha256=own_pin,
            numerical=numerical,formal_result=False,normal_accepted=False)
    finally:
        for module,name,original in originals: setattr(module,name,original)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-result-sha256',required=True)
    parser.add_argument('--expected-record-sha256',required=True)
    args=parser.parse_args()
    print(json.dumps(replay(args.expected_result_sha256,args.expected_record_sha256),sort_keys=True))
