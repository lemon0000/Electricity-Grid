from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

import pytest

from test_rq2_scale_normal_source_v1 import supplied as source_request
from test_rq2_scale_normal_source_v1 import declared_source, prepared_source, bound_source, source_supplied
from test_rq2_grid_information_v1 import declaration
from src.rq2_joint_deliverability_boundary_v1 import normal_numerical_source as api


@pytest.fixture
def observed(source_request):
    request, identity = source_request
    inputs, _ = api.source._prepare(request, identity)
    def builder():
        return api.acceptance.stream.build_continuous_normal_model(inputs,
            expected_identity=request.source.expected_input_identity,
            expected_implementation_identity=api.acceptance.stream.implementation_identity())
    model = builder()
    raw = api.capture.solve_once(builder, request.specification,
        expected_structure=api.capture.audit._structure(model),
        max_variables=request.source.expected_scale.variables,
        max_constraints=request.source.expected_scale.constraints,
        max_payload_bytes=api.LIMIT, expected_implementation=api.capture.implementation_identity())
    return request, declaration(inputs.carry.source_hour), raw


def pins(request, declared, raw):
    args = dict(expected_record_sha256=sha256(raw).hexdigest(), max_record_bytes=api.LIMIT)
    return dict(args, expected_binding_identity=api.binding_identity(request, declared, **args))


def project(observed):
    req, declared, raw = observed
    return api.prepare_information(raw, req, declared, **pins(req, declared, raw))


def test_rebuilt_source_and_accepted_plan_project_without_solver(observed, monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('read-only projection attempted solver')
    monkeypatch.setattr(api.capture, 'solve_once', forbidden)
    monkeypatch.setattr(api.capture.provenance.adapter, 'create_solver', forbidden)
    report, prepared = project(observed)
    assert report['numerical_plan_accepted'] and prepared is not None
    assert report['source_before'] == report['source_after']
    assert report['prepared_information_identity'] == prepared.audit_identity
    assert report['allowed_plan_identity'] == prepared.allowed_plan_identity
    assert report['assessment']['normal_witness_errors'] == []
    assert report['solver_calls_by_verifier'] == 0
    assert report['mechanism_initial_state'] and not report['observed_power_mapping']
    for key in ('formal_result', 'security_certified', 'rigorous_exact_optimality_certified',
                'native_execution_authenticated', 'whole_task_resources_verified', 'executable_resume_available'):
        assert report[key] is False
    assert all(h.information == observed[1] for h in prepared.hours)


@pytest.mark.parametrize('fault', ['record_hash', 'binding', 'size', 'extra', 'duplicate', 'options',
    'bool_calls', 'count', 'authority', 'residual', 'native_status', 'channel_error', 'assignment'])
def test_record_mismatch_never_produces_plan(observed, fault):
    req, declared, raw = observed
    args = pins(req, declared, raw)
    n = json.loads(raw)
    if fault == 'record_hash': args['expected_record_sha256'] = '0'*64
    elif fault == 'binding': args['expected_binding_identity'] = '0'*64
    elif fault == 'size': args['max_record_bytes'] = 1
    elif fault == 'duplicate': raw = raw[:-1]+b',"solver_calls":1}'
    else:
        if fault == 'extra': n['extra'] = 1
        elif fault == 'options': n['solver_options']['Threads'] = 2
        elif fault == 'bool_calls': n['solver_calls'] = True
        elif fault == 'count': n['variables'] += 1
        elif fault == 'authority': n['normal_accepted'] = True
        elif fault == 'residual': n['maximum_residual'] = .01
        elif fault == 'native_status': n['provenance']['native_status'] = 9
        elif fault == 'channel_error': n['provenance']['native']['ObjVal']['error'] = 'ignored'
        elif fault == 'assignment': n['assignment'].pop()
        raw = api.capture.encode(n)
    if fault not in ('record_hash', 'binding', 'size'):
        args = pins(req, declared, raw)
    with pytest.raises(ValueError): api.prepare_information(raw, req, declared, **args)


def test_missing_incumbent_is_unresolved_without_projection(observed, monkeypatch):
    req, declared, raw = observed
    n = json.loads(raw)
    n.update(provenance=None, assignment=None, assignment_valid=False, maximum_residual=None,
        maximum_integrality_violation=None, native_solution_count=0, native_status=9,
        pyomo_status='aborted', pyomo_termination='maxTimeLimit')
    def forbidden(*args, **kwargs): raise AssertionError('missing incumbent reached projection')
    monkeypatch.setattr(api.information, 'prepare_normal_information', forbidden)
    report, prepared = project((req, declared, api.capture.encode(n)))
    assert report['status'] == 'unresolved_source_projection' and prepared is None
    assert report['assessment'] is None and not report['numerical_plan_accepted']


def test_timeout_with_valid_incumbent_remains_unresolved(observed, monkeypatch):
    req, declared, raw = observed
    n = json.loads(raw)
    for obj in (n, n['provenance']):
        obj.update(native_status=9, pyomo_status='aborted', pyomo_termination='maxTimeLimit')
    n['provenance']['pyomo_solution_status'] = 'feasible'
    n['provenance']['optimal_status_channels_consistent'] = True
    def forbidden(*args, **kwargs): raise AssertionError('timeout reached accepted projection')
    monkeypatch.setattr(api.information, 'prepare_normal_information', forbidden)
    report, prepared = project((req, declared, api.capture.encode(n)))
    assert prepared is None and not report['numerical_plan_accepted']
    assert not report['assessment']['checks']['optimal_status']
    assert report['assessment']['normal_witness_errors'] == []


def test_future_information_declaration_refused(observed):
    req, declared, raw = observed
    with pytest.raises(ValueError, match='precede'):
        project((req, replace(declared, issued_at_source_hour=declared.issued_at_source_hour+1), raw))


def test_source_change_after_numerical_audit_prevents_return(observed, monkeypatch):
    req, declared, raw = observed
    original = api.acceptance.assess_assignment
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        path = Path(req.source.pair_declaration_path)
        path.write_bytes(path.read_bytes()+b'\n')  # pytest-owned source only
        return result
    monkeypatch.setattr(api.acceptance, 'assess_assignment', changed)
    with pytest.raises(ValueError): project(observed)


@pytest.mark.parametrize('fault', ['assignment', 'terminal'])
def test_projected_witness_substitution_refused(observed, monkeypatch, fault):
    original = api.information.prepare_normal_information
    def changed(*args, **kwargs):
        prepared = original(*args, **kwargs)
        if fault == 'assignment': object.__setattr__(prepared, 'normal_assignment_identity', '0'*64)
        else: object.__setattr__(prepared.normal_witness, 'terminal_carry', None)
        return prepared
    monkeypatch.setattr(api.information, 'prepare_normal_information', changed)
    with pytest.raises(ValueError, match='witness differs'): project(observed)


@pytest.mark.parametrize('field,value', [('threads', 2), ('random_seed', 1),
    ('feasibility_tolerance', 1e-6), ('expected_package_version', '0')])
def test_only_authorized_direct_solver_spec_can_bind(observed, field, value):
    req, declared, raw = observed
    spec = replace(req.specification, **{field: value})
    with pytest.raises(ValueError):
        execution = api.source.kernel.normal_execution_identity(req.source.expected_input_identity,
            req.source.expected_scale, spec, req.budget)
        changed = replace(req, specification=spec, expected_normal_execution_identity=execution)
        pins(changed, declared, raw)


@pytest.mark.parametrize('filename', ['normal_numerical_source.py', 'grid_information.py',
    'rq2_normal_numerical_acceptance_v1.py', 'rq2_objective_provenance_run_v1.py'])
def test_dependency_change_after_entry_cannot_return_plan(observed, monkeypatch, filename):
    req, declared, raw = observed
    args = pins(req, declared, raw)
    original = api.information.prepare_normal_information
    read = Path.read_bytes
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        monkeypatch.setattr(Path, 'read_bytes', lambda p: read(p)+b' ' if p.name == filename else read(p))
        return result
    monkeypatch.setattr(api.information, 'prepare_normal_information', changed)
    with pytest.raises(ValueError): api.prepare_information(raw, req, declared, **args)


def test_accepted_projection_uses_existing_source_and_current_information_interfaces(observed):
    from src.rq2_joint_deliverability_boundary_v1 import common_request_adapter as mapping
    req, declared, raw = observed
    report, prepared = project(observed)
    inputs, _ = api.source._prepare(req, api.source.request_identity(req))
    hour = inputs.source_hours[0]
    point = inputs.data.hourly_points[hour-1]
    units = prepared.network.units
    current = api.information.CurrentGridConditions(hour, prepared.hours[0].timestamp,
        tuple(sorted(point.demand_by_bus_mw.items())),
        tuple((g.uid, point.generator_min_mw[g.uid]) for g in units),
        tuple((g.uid, point.generator_max_mw[g.uid]) for g in units),
        tuple((g.uid, g.enabled) for g in units), inputs.request.dc_requested_mw[0],
        inputs.request.dc_physical_maximum_mw[0], inputs.request.dc_connected_capacity_mw[0],
        'mechanism_assumption')
    view = api.information.current_grid_information(prepared, current,
        expected_audit_identity=report['prepared_information_identity'])
    bound = mapping.bind_request_source(inputs, prepared, view,
        expected_normal_identity=req.source.expected_input_identity,
        expected_prepared_identity=prepared.audit_identity)
    assert bound.current_visible_identity == view.visible_identity
    assert view.normal.information.evidence_role == 'mechanism_assumption'
    assert not hasattr(view, 'source_request_identity') and not hasattr(view, 'assessment')


@pytest.mark.parametrize('fault', ['type', 'contract', 'source_input_identity',
    'implementation_sha256', 'causal_certificate', 'formal_result', 'hours', 'generation',
    'commitment', 'previous_commitment', 'information', 'allowed', 'network'])
def test_projection_substitution_cannot_rebind_source_or_plan(observed, monkeypatch, fault):
    original = api.information.prepare_normal_information
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        if fault == 'type':
            from types import SimpleNamespace
            return SimpleNamespace(**vars(result))
        if fault in ('contract', 'source_input_identity', 'implementation_sha256'):
            object.__setattr__(result, fault, '0'*64)
        elif fault in ('causal_certificate', 'formal_result'):
            object.__setattr__(result, fault, True)
        elif fault == 'hours': object.__setattr__(result, 'hours', result.hours[:-1])
        elif fault == 'generation': object.__setattr__(result.hours[0], 'generation_mw', ())
        elif fault in ('commitment', 'previous_commitment'):
            rows = getattr(result.hours[0], fault)
            object.__setattr__(result.hours[0], fault, tuple((uid, not on) for uid, on in rows))
        elif fault == 'information':
            object.__setattr__(result.hours[0], 'information', replace(observed[1], issued_at_source_hour=999))
        else:
            # Rebind both levels together: simple identity equality is insufficient.
            object.__setattr__(result, 'allowed_plan_identity', '0'*64)
            for h in result.hours: object.__setattr__(h, 'allowed_plan_identity', '0'*64)
            if fault == 'network':
                unit = result.network.units[0]
                object.__setattr__(unit, 'maximum_power_mw', unit.maximum_power_mw+1)
        return result
    monkeypatch.setattr(api.information, 'prepare_normal_information', changed)
    with pytest.raises(ValueError): project(observed)
