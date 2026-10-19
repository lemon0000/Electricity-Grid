from dataclasses import replace
from fractions import Fraction

import pytest
from pyomo.environ import Constraint, Var, value, minimize

from test_rq2_current_grid_step_v1 import prepared, current, view, origin, protocol, G, B
from test_rq2_continuous_grid_normal_v1 import fixture
from test_rq2_grid_information_v1 import prepare
from src.rq2_joint_deliverability_boundary_v1 import reference_grid as ref
from src.rq2_joint_deliverability_boundary_v1.event_disclosure import CurrentOutageReport, disclose_current


def args(*, ramp=10., demand=20., baseline=25., generation=20., initial_down=False, active=None, cap=None):
    info = view(prepared(ramp), replace(current(demand=demand), dc_baseline_mw=baseline))
    physical = origin(info, active=G if initial_down else None, generation=0. if initial_down else generation)
    before = ref.initialize_reference_origin(info, physical.disclosure,
        reference_protocol=ref.ReferenceProtocol(
            'common_baseline_no_cfe_no_recovery_assumed_prior_reference_fulfilment',
            'all_current_hours_mechanism', 'mechanism_assumption'),
        grid_protocol=protocol(), generation_mw=physical.generation_mw, base_availability=physical.base_availability)
    disclosure = disclose_current(physical.disclosure, CurrentOutageReport(1, active, cap))
    return info, disclosure, before


def assignment(inputs, p, generation, **changes):
    model = ref.build_reference_grid_model(*inputs, expected_identity=ref.reference_input_identity(*inputs))
    values = {v.name: 0. for v in model.component_data_objects(Var)}
    values.update({'reference_power': p, 'generation[G1]': generation})
    values.update(changes)
    return model, values


def audit(inputs, p, generation, **changes):
    model, values = assignment(inputs, p, generation, **changes)
    return ref.audit_reference_assignment(*inputs, values, expected_identity=ref.reference_input_identity(*inputs))


def no_selection(result):
    assert result.selected_request is result.next_reference_state is None
    assert result.minimum_request_certificate is result.causal_certificate is result.infeasibility_certificate is None
    assert not result.formal_result and not result.security_certified


@pytest.mark.parametrize('p,generation,valid', [(10., 30., True), (11., 31., False), (0., 20., True)])
def test_reference_request_boundary_and_nonminimal_feasible_assignment(p, generation, valid):
    inputs = args()
    result = audit(inputs, p, generation)
    assert result.physical_assignment_valid is valid
    assert inputs[2].physical_origin.source_hour == 0
    if valid:
        assert Fraction(*map(int, result.candidate_grid_request_exact)) == 25-Fraction(str(p))
        assert result.canonical_objective == 25-p
    else:
        assert result.candidate_grid_request_exact is None
    no_selection(result)


@pytest.mark.parametrize('p,valid', [(20., True), (15., True), (10., False), (0., False)])
def test_reducing_reference_power_is_not_a_monotone_feasibility_test(p, valid):
    inputs = args(demand=0., baseline=20., generation=25.)
    result = audit(inputs, p, p)
    assert result.physical_assignment_valid is valid
    if p == 10.:
        assert result.physical_witness.maximum_exact_violation == 5.
    no_selection(result)


@pytest.mark.parametrize('demand,valid', [(20., True), (0., False)])
def test_zero_baseline_requires_a_physical_witness(demand, valid):
    inputs = args(demand=demand, baseline=0.)
    result = audit(inputs, 0., demand)
    assert result.physical_assignment_valid is valid
    assert result.candidate_grid_request_exact == (('0', '1') if valid else None)
    no_selection(result)


@pytest.mark.parametrize('p', [-1e-12, 25.000000000001])
def test_reference_domain_is_not_relaxed_by_physical_tolerance(p):
    result = audit(args(), p, 20.+p)
    assert result.errors == ('reference_power_outside_exact_domain',)
    assert result.physical_witness is None
    assert not result.physical_assignment_valid


def test_power_is_a_decision_in_balance_and_correct_objective():
    inputs = args()
    model, values = assignment(inputs, 10., 30.)
    assert model.objective.sense == minimize
    assert model.reference_power.bounds == (0., 25.)
    for name, v in values.items():
        model.find_component(name).set_value(v)
    assert value(model.objective) == 15.
    assert all(abs(value(c.body)-value(c.lower)) < 1e-12 for c in model.balance.values())
    model.reference_power.set_value(11.)
    assert value(model.objective) == 14.
    assert any(abs(value(c.body)-value(c.lower)) == 1. for c in model.balance.values())


@pytest.mark.parametrize('p', [0., 5., 10., 15., 20., 25.])
def test_reference_and_fixed_projection_agree_for_complete_assignments(p):
    inputs = args()
    model, values = assignment(inputs, p, 20.+p)
    for name, v in values.items():
        model.find_component(name).set_value(v, skip_validation=True)
    violation = 0.
    for c in model.component_data_objects(Constraint, active=True):
        if c.lower is not None:
            violation = max(violation, value(c.lower)-value(c.body))
        if c.upper is not None:
            violation = max(violation, value(c.body)-value(c.upper))
    result = ref.audit_reference_assignment(*inputs, values, expected_identity=ref.reference_input_identity(*inputs))
    assert result.physical_assignment_valid == (violation <= 1e-6)


@pytest.mark.parametrize('cap,valid', [(10., True), (9., False)])
def test_repair_constraint_is_inherited(cap, valid):
    result = audit(args(ramp=60., demand=0., baseline=20., initial_down=True, cap=cap), 10., 10.)
    assert result.physical_assignment_valid is valid
    no_selection(result)


def test_generator_trip_zero_power_and_branch_outage_constraints():
    result = audit(args(demand=0., baseline=20., active=G), 0., 0.)
    assert result.physical_assignment_valid
    assert result.candidate_grid_request_exact == ('20', '1')
    inputs = args(active=B)
    bad = audit(inputs, 10., 30., **{'branch_flow[AC1]': 1.})
    assert not bad.physical_assignment_valid
    no_selection(result)


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'nan'])
def test_invalid_assignment_is_an_input_error(mutation):
    inputs = args()
    _, values = assignment(inputs, 10., 30.)
    if mutation == 'missing':
        del values['reference_power']
    elif mutation == 'extra':
        values['arm_id'] = 1.
    else:
        values['reference_power'] = float('nan')
    with pytest.raises(ValueError):
        ref.audit_reference_assignment(*inputs, values, expected_identity=ref.reference_input_identity(*inputs))


def test_arm_actual_state_cannot_be_passed_as_reference_origin():
    info, disclosure, before = args()
    with pytest.raises(ValueError, match='arm actual carry'):
        ref.reference_input_identity(info, disclosure, before.physical_origin)
    with pytest.raises(TypeError):
        replace(before, physical_origin=before.physical_origin)


@pytest.mark.parametrize('field', ['reference_rule', 'invocation_scope', 'evidence_role'])
def test_reference_mechanism_must_be_explicit(field):
    before = args()[2]
    with pytest.raises(ValueError):
        replace(before.protocol, **{field: 'different'})


def test_stale_identity_and_runtime_contract_drift(monkeypatch):
    inputs = args()
    with pytest.raises(ValueError, match='identity mismatch'):
        ref.build_reference_grid_model(*inputs, expected_identity='0'*64)
    witness = audit(inputs, 10., 30.)
    identity = witness.identity
    monkeypatch.setattr(ref, 'CONTRACT', 'changed')
    assert witness.identity == identity
    with pytest.raises(ValueError, match='contract drift'):
        ref.reference_input_identity(*inputs)


def test_audited_physical_carry_is_not_a_selected_reference_origin():
    inputs = args()
    result = audit(inputs, 10., 30.)
    physical = result.physical_witness.next_carry
    assert physical is not None
    with pytest.raises(ValueError, match='arm actual carry'):
        ref.reference_input_identity(inputs[0], inputs[1], physical)


def test_mutation_during_projection_audit_fails_closed(monkeypatch):
    inputs = args()
    original = ref.audit_current_grid_assignment
    def changed(*a, **kw):
        result = original(*a, **kw)
        monkeypatch.setattr(ref, 'CONTRACT', 'changed')
        return result
    monkeypatch.setattr(ref, 'audit_current_grid_assignment', changed)
    with pytest.raises(ValueError, match='contract drift'):
        audit(inputs, 10., 30.)


def test_reference_origin_cannot_skip_a_source_hour():
    info, disclosure, before = args()
    second_info = view(prepared(), current(2))
    with pytest.raises(ValueError, match='clock'):
        ref.reference_input_identity(second_info, disclosure, before)


def test_fresh_import_identity_dependency_closure():
    import json
    from pathlib import Path
    import subprocess
    import sys
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import SOURCE_DEPENDENCIES
    script = '''
import json, sys
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.reference_grid
root = Path.cwd()
print(json.dumps(sorted(Path(module.__file__).resolve().relative_to(root).as_posix()
    for name, module in sys.modules.items() if name == 'src' or name.startswith('src.'))))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script], check=True, capture_output=True,
        text=True, cwd=Path(__file__).resolve().parents[1], timeout=30)
    expected = set(SOURCE_DEPENDENCIES) | {
        'src/rq2_joint_deliverability_boundary_v1/'+name+'.py'
        for name in ('reference_grid', 'current_grid_step', 'grid_information', 'event_disclosure')}
    assert set(json.loads(result.stdout)) == expected


@pytest.mark.parametrize('entry', ['build', 'audit'])
@pytest.mark.parametrize('kind', ['equal_anything', 'str_subclass', 'uppercase', 'short', 'nonhex'])
def test_expected_identity_requires_builtin_canonical_digest(entry, kind):
    inputs = args()
    _, values = assignment(inputs, 10., 30.)
    class EqualAnything:
        def __eq__(self, other):
            return True
        def __ne__(self, other):
            return False
    class StringSubclass(str):
        pass
    identity = ref.reference_input_identity(*inputs)
    expected = {'equal_anything': EqualAnything(), 'str_subclass': StringSubclass(identity),
        'uppercase': identity.upper(), 'short': '0'*63, 'nonhex': 'g'*64}[kind]
    with pytest.raises(ValueError, match='canonical lowercase SHA256'):
        if entry == 'build':
            ref.build_reference_grid_model(*inputs, expected_identity=expected)
        else:
            ref.audit_reference_assignment(*inputs, values, expected_identity=expected)


def test_reference_power_enters_remote_dc_bus_and_preserves_network_balance():
    normal = fixture()
    normal = replace(normal, request=replace(normal.request, dc_bus=2))
    info = view(prepare(normal), replace(current(demand=20.), dc_baseline_mw=25.))
    physical = origin(info)
    reference = ref.initialize_reference_origin(info, physical.disclosure,
        reference_protocol=args()[2].protocol, grid_protocol=protocol(),
        generation_mw=physical.generation_mw, base_availability=physical.base_availability)
    disclosure = disclose_current(physical.disclosure, CurrentOutageReport(1, B, None))
    inputs = info, disclosure, reference
    model, values = assignment(inputs, 10., 30., **{'dc_flow[DC1]': 10.})
    for name, number in values.items():
        model.find_component(name).set_value(number)
    assert all(value(c.body) == value(c.lower) for c in model.balance.values())
    assert audit(inputs, 10., 30., **{'dc_flow[DC1]': 10.}).physical_assignment_valid
    assert not audit(inputs, 10., 30.).physical_assignment_valid
