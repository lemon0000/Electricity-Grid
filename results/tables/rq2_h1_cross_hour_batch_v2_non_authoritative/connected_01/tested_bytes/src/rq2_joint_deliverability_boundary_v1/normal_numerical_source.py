"""Source-bound numerical normal replay and plan projection; no execution.

The caller retains the record and binding pins independently. This verifies
correspondence to rebuilt inputs, not the historical origin of native channels.
"""
from copy import deepcopy
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path

from . import scale_normal_source as source, grid_information as information
from .continuous_grid_normal import NormalAssignmentWitness
from ..solvers import rq2_objective_provenance_run_v1 as capture
from ..solvers import rq2_normal_numerical_acceptance_v1 as acceptance

SCHEMA = 'draft_source_bound_numerical_normal_information_v1'
LIMIT = 16*1024**2
NUMERICAL_KEYS = frozenset(('schema', 'implementation_identity', 'model_structure_identity',
    'solver_calls', 'variables', 'constraints', 'solver_options', 'pyomo_status', 'pyomo_termination',
    'native_status', 'native_solution_count', 'provenance', 'assignment', 'maximum_residual',
    'maximum_integrality_violation', 'assignment_valid', 'formal_result', 'normal_accepted',
    'optimality_certified'))
PROVENANCE_KEYS = frozenset(('schema', 'adapter_identity', 'collector_sha256', 'native', 'native_status',
    'native_solution_count', 'native_model_sense', 'is_mip', 'pyomo_status', 'pyomo_termination',
    'pyomo_solution_status', 'optimal_status_channels_consistent', 'pyomo_lower_hex',
    'pyomo_upper_hex', 'pyomo_lower_source', 'canonical_objective_hex', 'exact_objective',
    'constant_hex', 'ordered_objective_terms', 'native_constant_hex', 'ordered_native_objective_terms',
    'native_exact_objective', 'native_exact_value_equals_canonical_exact_value',
    'canonical_objective_algebra', 'native_objective_algebra', 'native_algebra_equals_canonical_algebra',
    'referenced_assignment', 'assignment_sha256', 'comparisons', 'formal_result',
    'optimality_certified', 'native_execution_authenticated', 'solver_calls_by_collector'))


def implementation_identity():
    return source.kernel._digest(SCHEMA, capture.implementation_identity(),
        acceptance.stream.implementation_identity(), source.kernel.streaming.legacy._digest(
            source.kernel.streaming.legacy._dependencies()),
        tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest()) for m in
              (source, information, acceptance, acceptance.predicate, acceptance.replay_helper)),
        sha256(Path(__file__).read_bytes()).hexdigest())


def binding_identity(request, declaration, *, expected_record_sha256, max_record_bytes):
    source.kernel._pin(expected_record_sha256)
    if type(max_record_bytes) is not int or not 0 < max_record_bytes <= LIMIT:
        raise ValueError('bounded numerical record required')
    if type(declaration) is not information.PlanInformationDeclaration:
        raise ValueError('typed pre-episode information declaration required')
    declaration.__post_init__()
    pin = source.request_identity(request)
    capture.provenance.adapter.validate_spec(request.specification)
    return source.kernel._digest(SCHEMA, pin, declaration, expected_record_sha256,
                                 max_record_bytes, implementation_identity())


def _hex(value):
    if type(value) is not str:
        raise ValueError('canonical finite hex required')
    number = float.fromhex(value)
    if not isfinite(number) or number.hex() != value:
        raise ValueError('canonical finite hex required')
    return number


def _validate(n, request):
    if type(n) is not dict or set(n) != NUMERICAL_KEYS:
        raise ValueError('exact numerical report inventory required')
    scale = request.source.expected_scale
    if (n['schema'] != 'rq2_objective_provenance_owned_solve_v1'
            or n['implementation_identity'] != capture.implementation_identity()
            or type(n['solver_calls']) is not int or n['solver_calls'] != 1
            or type(n['variables']) is not int or n['variables'] != scale.variables
            or type(n['constraints']) is not int or n['constraints'] != scale.constraints
            or capture.encode(n['solver_options']) != capture.encode(capture.audit.solver_options(request.specification))
            or any(n[k] is not False for k in ('formal_result', 'normal_accepted', 'optimality_certified'))
            or type(n['assignment_valid']) is not bool
            or type(n['native_status']) is not int or n['native_status'] <= 0
            or type(n['native_solution_count']) is not int or n['native_solution_count'] < 0
            or any(type(n[k]) is not str for k in ('pyomo_status', 'pyomo_termination'))):
        raise ValueError('numerical report binding or authority mismatch')
    source.kernel._pin(n['model_structure_identity'])
    p = n['provenance']
    if p is None:
        if (n['assignment'] is not None or n['assignment_valid'] is not False
                or n['maximum_residual'] is not None or n['maximum_integrality_violation'] is not None):
            raise ValueError('missing provenance cannot publish assignment')
        return False
    if (type(p) is not dict or set(p) != PROVENANCE_KEYS or type(p['native']) is not dict
            or set(p['native']) != {'ObjVal', 'ObjBound', 'ObjBoundC', 'Runtime'}):
        raise ValueError('exact provenance inventory required')
    if (p['schema'] != 'rq2_objective_provenance_v1'
            or p['collector_sha256'] != sha256(Path(capture.provenance.__file__).read_bytes()).hexdigest()
            or p['adapter_identity'] != capture.provenance.adapter.implementation_identity()
            or any(p[k] is not False for k in ('formal_result', 'optimality_certified', 'native_execution_authenticated'))
            or type(p['solver_calls_by_collector']) is not int or p['solver_calls_by_collector'] != 0
            or type(p['native_model_sense']) is not int or p['native_model_sense'] != 1
            or p['is_mip'] is not True or p['pyomo_lower_source'] != 'ObjBound'
            or any(type(p[k]) is not int or p[k] != n[k] for k in ('native_status', 'native_solution_count'))
            or any(p[k] != n[k] for k in ('pyomo_status', 'pyomo_termination'))
            or type(p['pyomo_solution_status']) is not str):
        raise ValueError('direct provenance metadata mismatch')
    consistent = ((p['native_status'] == 2) == (p['pyomo_termination'] == 'optimal')
                  == (p['pyomo_solution_status'] == 'optimal')
                  and (p['native_status'] != 2 or p['pyomo_status'] == 'ok'))
    if p['optimal_status_channels_consistent'] is not consistent:
        raise ValueError('optimal status consistency flag mismatch')
    for key in p['native']:
        channel = p['native'][key]
        if (type(channel) is not dict or set(channel) != {'available', 'hex', 'error'}
                or channel['available'] is not True or channel['error'] is not None):
            raise ValueError('complete finite native channel required')
        number = _hex(channel['hex'])
        if key == 'Runtime' and number < 0:
            raise ValueError('nonnegative native runtime required')
    for key in ('maximum_residual', 'maximum_integrality_violation'):
        if type(n[key]) not in (int, float) or not isfinite(n[key]) or n[key] < 0:
            raise ValueError('finite nonnegative residual required')
    return True


def _check_projection(prepared, inputs, assignment, declaration, assessment):
    """Reconstruct identity material independently of the projection producer."""
    fields = dict(assessment['normal_witness'][1])
    if type(prepared) is not information.PreparedNormalInformation:
        raise ValueError('exact prepared information type required')
    witness = prepared.normal_witness
    if (type(witness) is not NormalAssignmentWitness
            or prepared.contract != information.CONTRACT
            or prepared.source_input_identity != fields['input_identity']
            or prepared.normal_assignment_identity != fields['assignment_identity']
            or prepared.implementation_sha256 != sha256(Path(information.__file__).read_bytes()).hexdigest()
            or prepared.causal_certificate is not None or prepared.formal_result is not False
            or source.kernel._encode(witness)[0] != assessment['normal_witness'][0]
            or witness.input_identity != fields['input_identity']
            or witness.assignment_identity != fields['assignment_identity']
            or witness.errors != ()
            or witness.evidence_role != 'derived_normal_assignment_development_witness'
            or source.kernel._encode(witness.terminal_carry) != fields['terminal_carry']
            or any(type(x) not in (int, float) or not isfinite(x) or not 0 <= x <= 1e-9
                   for x in (witness.maximum_constraint_violation, witness.maximum_integrality_violation))):
        raise ValueError('projected plan witness differs from accepted assignment')
    data = inputs.data
    generators = sorted(data.generators, key=lambda g: g.uid)
    owned = information._owned
    network = owned(information.StaticNetwork, base_mva=data.base_mva,
        reference_bus=data.reference_bus, buses=tuple(sorted(b.uid for b in data.buses)),
        dc_bus=inputs.request.dc_bus,
        units=tuple(owned(information.StaticUnit, uid=g.uid, bus=g.bus,
            dispatch_mode=g.dispatch_mode, enabled=g.enabled, minimum_power_mw=g.p_min_mw,
            maximum_power_mw=g.p_max_mw, ramp_mw_per_hour=g.ramp_mw_per_hour) for g in generators),
        ac_branches=tuple(owned(information.StaticAcBranch, uid=b.uid, from_bus=b.from_bus,
            to_bus=b.to_bus, reactance_pu=b.reactance_pu, tap_ratio=b.tap_ratio,
            continuous_rating_mw=b.continuous_rating_mw) for b in sorted(data.branches, key=lambda b: b.uid)),
        dc_branches=tuple(owned(information.StaticDcBranch, uid=b.uid, from_bus=b.from_bus,
            to_bus=b.to_bus, minimum_power_mw=b.p_min_mw, maximum_power_mw=b.p_max_mw)
            for b in sorted(data.dc_branches, key=lambda b: b.uid)))
    previous = tuple((g.uid, inputs.initial.commitment[g.uid]
        if g.dispatch_mode == 'committable' else g.enabled) for g in generators)
    rows, forecasts = [], []
    for t, hour in enumerate(inputs.source_hours):
        stamp = inputs.request.timestamps[t].isoformat()
        on = tuple((g.uid, bool(round(assignment[f'commitment[{t},{g.uid}]']))
            if g.dispatch_mode == 'committable' else g.enabled) for g in generators)
        generation = tuple((g.uid, assignment[f'generation[normal,{t},{g.uid}]']) for g in generators)
        rows.append((hour, stamp, generation, on, previous))
        previous = on
        point = data.hourly_points[hour-1]
        forecasts.append((hour, stamp, tuple(sorted(point.demand_by_bus_mw.items())),
            tuple(sorted(point.generator_min_mw.items())), tuple(sorted(point.generator_max_mw.items())),
            tuple(sorted(point.spin_up_requirement_by_area_mw.items())),
            inputs.request.dc_requested_mw[t], inputs.request.dc_physical_maximum_mw[t],
            inputs.request.dc_connected_capacity_mw[t]))
    initial = tuple((g.uid, inputs.initial.commitment[g.uid], inputs.initial.generation_mw[g.uid],
        inputs.initial.time_in_state_hours[g.uid]) for g in generators)
    parameters = (tuple(sorted((b.uid, b.area) for b in data.buses)),
        tuple((g.uid, g.category, g.ramp_mw_per_minute, g.minimum_up_time_hours,
            g.minimum_down_time_hours, g.cold_start_cost_usd, g.shutdown_cost_usd,
            g.cost_breakpoints_mw, g.cost_values_usd_per_hour) for g in generators))
    allowed = information._digest(information.CONTRACT, declaration, network,
        tuple(forecasts), initial, parameters, tuple(rows))
    hours = tuple(owned(information.NormalHourView, source_hour=h, timestamp=s,
        information=declaration, generation_mw=g, commitment=c, previous_commitment=p,
        allowed_plan_identity=allowed) for h, s, g, c, p in rows)
    if (source.kernel._encode(prepared.network) != source.kernel._encode(network)
            or source.kernel._encode(prepared.hours) != source.kernel._encode(hours)
            or prepared.allowed_plan_identity != allowed):
        raise ValueError('projected network or complete plan differs from accepted source')


def prepare_information(data, request, declaration, *, expected_record_sha256,
                        expected_binding_identity, max_record_bytes):
    """Return (audit report, prepared plan or None), with zero solver calls.

    The numerical record is exactly the generic owned collector's output bytes.
    The binding pin covers source request, information declaration, implementation
    and external record digest. No process, capacity or formal authority follows.
    """
    request, declaration = deepcopy((request, declaration))
    source.kernel._pin(expected_binding_identity)
    def check():
        if binding_identity(request, declaration, expected_record_sha256=expected_record_sha256,
                max_record_bytes=max_record_bytes) != expected_binding_identity:
            raise ValueError('numerical source binding drift')
    check()
    if (type(data) is not bytes or len(data) > max_record_bytes
            or sha256(data).hexdigest() != expected_record_sha256):
        raise ValueError('external numerical record size/hash mismatch')
    n = json.loads(data)
    if capture.encode(n) != data:
        raise ValueError('canonical numerical record bytes required')
    has_assignment = _validate(n, request)
    identity = source.request_identity(request)
    declarations = source._declarations(request)
    inputs, before = source._prepare(request, identity)
    if declaration.issued_at_source_hour > inputs.carry.source_hour:
        raise ValueError('normal schedule must precede first action')
    model = acceptance.stream.build_continuous_normal_model(inputs,
        expected_identity=request.source.expected_input_identity,
        expected_implementation_identity=acceptance.stream.implementation_identity())
    if capture.audit._structure(model) != n['model_structure_identity']:
        raise ValueError('source model structure mismatch')
    del model
    assessment = prepared = None
    if has_assignment:
        assessment = acceptance.assess_assignment(inputs, n,
            expected_input_identity=request.source.expected_input_identity,
            expected_runner_identity=capture.implementation_identity(),
            expected_collector_sha256=sha256(Path(capture.provenance.__file__).read_bytes()).hexdigest(),
            expected_adapter_identity=capture.provenance.adapter.implementation_identity())
        if assessment['numerical_solver_optimality_accepted']:
            assignment = {name: _hex(value) for name, value in n['assignment']}
            prepared = information.prepare_normal_information(inputs, assignment,
                expected_input_identity=request.source.expected_input_identity, declaration=declaration)
            _check_projection(prepared, inputs, assignment, declaration, assessment)
    _, after = source._prepare(request, identity)
    if before != after or source._declarations(request) != declarations:
        raise ValueError('source changed during numerical projection')
    check()
    report = dict(schema=SCHEMA, binding_identity=expected_binding_identity,
        source_request_identity=identity, numerical_record_sha256=expected_record_sha256,
        source_before=before, source_after=after, assessment=assessment,
        declaration=source.kernel._encode(declaration),
        prepared_information_identity=None if prepared is None else prepared.audit_identity,
        allowed_plan_identity=None if prepared is None else prepared.allowed_plan_identity,
        status='numerically_accepted_source_projection' if prepared is not None else 'unresolved_source_projection',
        source_correspondence_rechecked=True, numerical_plan_accepted=prepared is not None,
        mechanism_initial_state=True, observed_power_mapping=False, registered_coupling=False,
        solver_calls_by_verifier=0, native_execution_authenticated=False, whole_task_resources_verified=False,
        rigorous_exact_optimality_certified=False, security_certified=False, formal_result=False,
        executable_resume_available=False)
    return report, prepared
