"""Reproduce a saved H25 objective discrepancy without calling any solver."""
from fractions import Fraction as Q
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from pyomo.environ import Objective, Var, value
from pyomo.repn.standard_repn import generate_standard_repn
from src.rq2_joint_deliverability_boundary_v1 import scale_normal_transport as transport

BASE = ROOT/'results/tables/rq2_scale_normal_h25_600s_attempt1_non_authoritative'
RESULT_PIN = '63c235412a86c43f92d7a37047ff99b1693e579b323e62794980e25113344103'
RECORD_PIN = '9f40ab3aede1115c0dd229aba410b8f2739f383b26e76c6593d129f7072fa00a'
PACKET_PIN = 'da633e1120ed768ab1b6a8d1030338c328bd9f56e6cd2917e4305bdf48ac2ade'


def decode(x):
    if type(x) is not list: return x
    if x[0] == 'float': return float.fromhex(x[1])
    if x[0] == 'tuple': return tuple(decode(y) for y in x[1])
    raise ValueError('unexpected numeric wire')


def diagnose():
    source = transport.source
    read = source.prepare._read_pinned
    script_pin = sha256(Path(__file__).read_bytes()).hexdigest()
    result_raw = read(BASE/'result.json', RESULT_PIN, 16*1024**2)
    record_raw = read(BASE/'normal_non_authoritative/normal_record.json', RECORD_PIN, 32*1024**2)
    request = transport.read_request(ROOT/'configs/rq2_scale_normal_h25_600s_request_v1.DRAFT.json',
        expected_sha256=PACKET_PIN, max_request_bytes=transport.LIMIT)
    request_pin = source.request_identity(request)
    result, record = json.loads(result_raw), json.loads(record_raw)
    if result['status'] != 'replayed_unresolved_normal' or not result['audit']['record_consistent']:
        raise ValueError('expected completed unresolved replay required')
    fields = dict(record['normal_record']['result'][1])
    native = dict(fields['normal'][1])
    assignment = dict(decode(native['loaded_values']))
    objective, lower, upper = (decode(native[k]) for k in ('objective', 'lower', 'upper'))
    targets = ((source, 'run_source'), (source.kernel, 'run_normal_only'),
        (source.kernel.native, '_solve'), (source.kernel.native, 'create_solver'))
    originals = [(module, name, getattr(module, name)) for module, name in targets]
    def forbidden(*args, **kwargs): raise RuntimeError('solver forbidden in objective diagnosis')
    try:
        for module, name in targets: setattr(module, name, forbidden)
        inputs, _ = source._prepare(request, request_pin)
        stream = source.kernel.streaming
        model = stream.build_continuous_normal_model(inputs, expected_identity=request.source.expected_input_identity,
            expected_implementation_identity=stream.implementation_identity())
        structure = source.kernel.native._structure(model)
        if structure != decode(native['structures'])[0]: raise ValueError('canonical structure mismatch')
        for variable in model.component_data_objects(Var):
            variable.set_value(assignment[variable.name], skip_validation=True)
        expr = next(model.component_data_objects(Objective)).expr
        if float(value(expr)) != objective: raise ValueError('recorded objective not reproduced')
        repn = generate_standard_repn(expr, compute_values=True)
        if not repn.is_linear(): raise ValueError('linear objective required')
        constant = float(repn.constant)
        exact, terms, products = Q.from_float(constant), [], []
        for variable, coefficient in zip(repn.linear_vars, repn.linear_coefs, strict=True):
            coefficient, assigned = float(coefficient), assignment[variable.name]
            exact += Q.from_float(coefficient)*Q.from_float(assigned)
            products.append(coefficient*assigned)
            terms.append((variable.name, coefficient.hex(), assigned.hex()))
        inventory = json.dumps(dict(constant_hex=constant.hex(), ordered_terms=terms),
            sort_keys=True, allow_nan=False).encode()
        if source.request_identity(request) != request_pin:
            raise ValueError('source/implementation drift')
        if read(BASE/'result.json', RESULT_PIN, 16*1024**2) != result_raw:
            raise ValueError('result drift')
        if read(BASE/'normal_non_authoritative/normal_record.json', RECORD_PIN, 32*1024**2) != record_raw:
            raise ValueError('record drift')
        if sha256(Path(__file__).read_bytes()).hexdigest() != script_pin:
            raise ValueError('diagnostic implementation drift')
        rational = lambda x: dict(numerator=str(x.numerator), denominator=str(x.denominator))
        return dict(schema='rq2_h25_objective_consistency_reproduction_v1', generator_sha256=script_pin,
            result_sha256=RESULT_PIN, record_sha256=RECORD_PIN, request_sha256=PACKET_PIN,
            request_identity=request_pin, model_structure_identity=structure,
            ordered_binary64_objective_inventory_sha256=sha256(inventory).hexdigest(),
            objective_linear_terms=len(terms), recorded_objective=objective, recorded_lower=lower, recorded_upper=upper,
            objective_ulp=math.ulp(objective), lower_minus_objective=lower-objective,
            exact_objective=rational(exact), exact_objective_minus_lower=rational(exact-Q.from_float(lower)),
            exact_objective_nearest_float=float(exact), fsum_of_rounded_products=math.fsum([constant, *products]),
            strict_lower_le_recorded_objective=lower <= objective, strict_lower_le_exact_objective=Q.from_float(lower) <= exact,
            solver_calls_by_diagnosis=0, formal_result=False, normal_accepted=False,
            scope='saved_assignment_objective_only_not_optimality_certificate')
    finally:
        for module, name, original in originals: setattr(module, name, original)


if __name__ == '__main__':
    print(json.dumps(diagnose(), sort_keys=True, allow_nan=False))
