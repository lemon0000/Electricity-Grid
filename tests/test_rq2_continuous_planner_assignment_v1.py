from dataclasses import replace
from fractions import Fraction as Q

import pytest
from pyomo.environ import Var, Constraint, Objective, Block, maximize

from test_rq2_continuous_planner_v1 import inputs, scenario, build, assign
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import NETWORK, CFE, JOINT, B6
from src.rq2_joint_deliverability_boundary_v1.planner_assignment import (
    audit_planner_assignment, audit_raw_solver_outcome,
)
from src.rq2_joint_deliverability_v2.solver_adapter import Rq2SolverSpec


SPEC = Rq2SolverSpec('highs', 'test-only-no-solver', 1, 1e-6, 1e-8, 1e-8, 1e-5, 0, 1., False)


def fixture(contract=None, arm=JOINT, **assignment):
    contract = inputs() if contract is None else contract
    model = build(contract, arm)
    assign(model, **assignment)
    return contract, model


def audit(contract, model, arm=JOINT, spec=SPEC):
    return audit_planner_assignment(contract, arm, model, spec)


@pytest.mark.parametrize('arm,peak', [(NETWORK, '.25'), (CFE, '.125'), (JOINT, '.375'), (B6, '.25')])
def test_four_arm_canonical_residual_and_exact_extraction(arm, peak):
    contract, model = fixture(inputs(scenario(g=(.25,), c=(.125,))), arm)
    result = audit(contract, model, arm)
    assert result.complete_assignment and result.structure_matches
    assert result.numerical_assignment_accepted and result.exact_witness_accepted
    assert result.maximum_bound_violation == result.maximum_integrality_violation == result.maximum_constraint_violation == 0
    assert result.witness.witness_capacity == Q(peak)
    assert len(result.snapshot) == len(result.variable_residuals)
    assert len(result.constraint_residuals) == len(list(model.component_data_objects(Constraint)))
    assert result.evidence()['prefix_upper_bound'] is None
    if arm == B6:
        assert result.witness.evidence()['scope'] == 'b6_separate_planning'


@pytest.mark.parametrize('valid', [False, True])
def test_deactivation_cannot_hide_canonical_constraint_failure(valid):
    contract, model = fixture(capacity=.25 if valid else .1)
    for component in model.component_objects(Constraint):
        component.deactivate()
    result = audit(contract, model)
    assert not result.structure_matches
    assert result.numerical_assignment_accepted is valid
    assert result.exact_witness_accepted is valid
    if not valid:
        assert result.maximum_constraint_violation > .14


@pytest.mark.parametrize('kind', ['constraint', 'objective', 'sense', 'bound', 'domain', 'fixed', 'nonlinear'])
def test_same_inventory_does_not_prove_structure_identity(kind):
    contract, model = fixture()
    if kind == 'constraint': model.service[1].set_value(model.grid_service['s', 0] == .1)
    elif kind == 'objective': model.minimum_capacity.set_value(2*model.capacity)
    elif kind == 'sense': model.minimum_capacity.sense = maximize
    elif kind == 'bound': model.capacity.setub(2)
    elif kind == 'domain': model.on['s', 'shared', 0].domain = model.capacity.domain
    elif kind == 'fixed': model.capacity.fix(.25)
    else: model.minimum_capacity.set_value(model.capacity**2)
    result = audit(contract, model)
    assert not result.structure_matches
    assert result.numerical_assignment_accepted and result.exact_witness_accepted
    if kind == 'nonlinear': assert result.structure_error == 'nonlinear submitted structure'


@pytest.mark.parametrize('raw,error', [(None, 'missing_value'), (float('nan'), 'nonfinite_value'),
    (float('inf'), 'nonfinite_value'), (True, 'unsupported_numeric_type')])
def test_unset_and_nonfinite_values_are_retained_and_unassessed(raw, error):
    contract, model = fixture()
    model.capacity.set_value(raw, skip_validation=True)
    result = audit(contract, model)
    row = dict(result.snapshot)['capacity']
    assert row.error == error and row.raw_repr == repr(raw)
    assert not result.complete_assignment and not result.numerical_assignment_accepted
    assert result.witness is None and result.evaluation_error == 'incomplete_or_invalid_assignment'
    assert result.maximum_bound_violation is result.maximum_integrality_violation is result.maximum_constraint_violation is None


@pytest.mark.parametrize('kind', ['missing', 'extra', 'inactive_extra'])
def test_complete_inventory_includes_inactive_blocks(kind):
    contract, model = fixture()
    if kind == 'missing': model.del_component(model.remaining)
    elif kind == 'extra': model.unexpected = Var(initialize=0.)
    else:
        model.hidden = Block()
        model.hidden.extra = Var(initialize=0.)
        model.hidden.deactivate()
    result = audit(contract, model)
    assert not result.complete_assignment and result.witness is None
    if kind == 'missing': assert result.missing_variables
    else: assert result.extra_variables == (('unexpected',) if kind == 'extra' else ('hidden.extra',))


def test_separate_integer_and_continuous_tolerances_and_no_clipping():
    contract, model = fixture()
    model.on['s', 'shared', 0].set_value(.999999, skip_validation=True)
    model.start['s', 'shared', 0].set_value(.999999, skip_validation=True)
    model.allocation['s', 'shared', 0, 0].set_value(-1e-12, skip_validation=True)
    result = audit(contract, model)
    assert result.maximum_integrality_violation > 9e-7
    assert result.maximum_bound_violation == 1e-12
    assert result.numerical_assignment_accepted  # Separate 1e-5 integer and 1e-8 continuous thresholds.
    assert not result.exact_witness_accepted and result.extraction_error
    assert dict(result.snapshot)['allocation[s,shared,0,0]'].number == -1e-12
    strict = audit(contract, model, spec=replace(SPEC, integer_feasibility_tolerance=1e-8))
    assert not strict.numerical_assignment_accepted


def test_shortest_decimal_is_not_repaired_to_original_request():
    contract, model = fixture(inputs(scenario(g=(.1,))), grid={('s', 0): .09999999999999998})
    result = audit(contract, model)
    assert result.numerical_assignment_accepted and not result.exact_witness_accepted
    row = dict(result.snapshot)['grid_service[s,0]']
    assert row.raw_repr == '0.09999999999999998'
    assert float.fromhex(row.float_hex) == row.number
    assert result.witness.candidate.scenarios[0][1][0].grid_service == Q('0.09999999999999998')


def test_relaxed_micro_recovery_is_not_physical_witness():
    contract, model = fixture(inputs(scenario(g=(.25, 0.))),
        recovery={('s', 'shared', 1): 5e-7}, allocations={('s', 'shared', 0, 1): 4e-7})
    result = audit(contract, model)
    assert result.numerical_assignment_accepted and not result.exact_witness_accepted
    action = result.witness.candidate.scenarios[0][1][1].tracks[0][1]
    assert action.recovery == Q('5e-7') and action.allocations == ((1, Q('4e-7')),)


def test_nonzero_micro_allocation_is_not_dropped_and_signed_zero_is_preserved():
    contract, model = fixture()
    model.allocation['s', 'shared', 0, 0].set_value(1e-16)
    model.recovery['s', 'shared', 0].set_value(-0.)
    result = audit(contract, model)
    assert result.numerical_assignment_accepted and not result.exact_witness_accepted
    action = result.witness.candidate.scenarios[0][1][0].tracks[0][1]
    assert action.allocations == ((1, Q('1e-16')),)
    assert dict(result.snapshot)['recovery[s,shared,0]'].float_hex == '-0x0.0p+0'


def test_trusted_inputs_not_model_metadata_and_spec_validation():
    contract, model = fixture()
    model._continuous_inputs = inputs(scenario(g=(.75,)))
    model._continuous_planner_id = 'forged'
    assert audit(contract, model).exact_witness_accepted
    altered = audit(inputs(scenario(g=(.75,))), model)
    assert not altered.numerical_assignment_accepted and not altered.exact_witness_accepted
    with pytest.raises(ValueError): audit(contract, model, spec=replace(SPEC, feasibility_tolerance=-1))


@pytest.mark.parametrize('termination,lower,upper,issue', [
    ('maxTimeLimit', .2, .25, 'termination_not_optimal'),
    ('infeasible', None, None, 'termination_not_optimal'),
    ('optimal', None, .25, 'lower_missing_value'),
    ('optimal', float('nan'), .25, 'lower_nonfinite_value'),
    ('optimal', .3, .25, 'inverted_bounds'),
    ('optimal', .2, .3, 'upper_differs_from_assignment_objective'),
    ('optimal', .26, .3, 'lower_exceeds_assignment_objective'),
])
def test_raw_outcome_failures_never_promote_bounds(termination, lower, upper, issue):
    result = audit(*fixture())
    outcome = audit_raw_solver_outcome(result, solver_status='ok', termination=termination,
                                      lower_bound=lower, upper_bound=upper)
    assert issue in outcome.issues
    assert outcome.evidence()['status'] == 'unresolved'
    assert outcome.evidence()['relaxed_prefix_capacity_interval'] is None
    if issue == 'inverted_bounds': assert outcome.absolute_gap is None


def test_even_consistent_raw_optimal_report_lacks_solver_lineage():
    result = audit(*fixture())
    outcome = audit_raw_solver_outcome(result, solver_status='ok', termination='optimal',
                                      lower_bound=.2, upper_bound=.25)
    assert outcome.absolute_gap == pytest.approx(.05)
    assert outcome.incumbent_relative_gap == pytest.approx(.2)
    assert outcome.issues == ('solver_input_and_bound_lineage_unaudited',)
    assert outcome.evidence()['status'] == 'unresolved'


def test_timeout_without_incumbent_keeps_raw_bound_and_missing_assignment():
    contract, model = fixture()
    model.capacity.set_value(None)
    result = audit(contract, model)
    outcome = audit_raw_solver_outcome(result, solver_status='warning', termination='maxTimeLimit',
                                      lower_bound=.2, upper_bound=None)
    assert outcome.lower.number == .2 and outcome.absolute_gap is None
    assert 'canonical_assignment_unaccepted' in outcome.issues


@pytest.mark.parametrize('arm', [JOINT, B6])
def test_valid_recovery_extracts_absolute_birth_and_binds_assignment(arm):
    s = scenario(g=(.25, 0.), c=(0., .125 if arm == B6 else 0.), due=(2, 4 if arm == B6 else None))
    observations = []
    for current in s.observations:
        observation = current.observation
        raw = observation.hour
        observations.append(replace(current, observation=replace(observation,
            hour=replace(raw, power_source_hour=raw.power_source_hour+30, workload_source_hour=raw.workload_source_hour+30),
            due_hour=None if observation.due_hour is None else observation.due_hour+30)))
    s = replace(s, anchor=replace(s.anchor, power_source_hour=30, workload_source_hour=130), observations=tuple(observations))
    track = 'grid' if arm == B6 else 'shared'
    contract, model = fixture(inputs(s), arm, recovery={('s', track, 1): .3125},
        allocations={('s', track, 0, 1): .25})
    result = audit(contract, model, arm)
    assert result.numerical_assignment_accepted and result.exact_witness_accepted
    actions = dict(result.witness.candidate.scenarios[0][1][1].tracks)
    assert actions[track].allocations == ((31, Q('.25')),)
    assert ('grid' if arm == B6 else 'shared', 31, 'recovered_by_deadline') in result.witness.scenarios[0].cohort_statuses
    before = result.assignment_id
    model.capacity.set_value(.5)
    changed = audit(contract, model, arm)
    assert changed.assignment_id != before
    outcome = audit_raw_solver_outcome(changed, solver_status='ok', termination='optimal', lower_bound=.25, upper_bound=.5)
    assert outcome.assignment_id == changed.assignment_id


def test_numeric_identity_preserves_invalid_large_integer_and_raw_bound_overflow():
    contract, model = fixture()
    model.capacity.set_value(2**53+1, skip_validation=True)
    result = audit(contract, model)
    assert dict(result.snapshot)['capacity'].error == 'lossy_integer_conversion'
    assert len(result.assignment_id) == 64
    outcome = audit_raw_solver_outcome(result, solver_status='ok', termination='optimal', lower_bound=-1e308, upper_bound=1e308)
    assert outcome.absolute_gap is None and 'gap_overflow' in outcome.issues


@pytest.mark.parametrize('fault', ['clear_residuals', 'objective', 'evaluation', 'cross_witness', 'cross_inputs', 'snapshot_number', 'snapshot_hex', 'duplicate_variable'])
def test_public_audit_cannot_be_relabelled_or_spliced(fault):
    failed = audit(*fixture(capacity=.1))
    valid = audit(*fixture())
    changes = {}
    if fault == 'clear_residuals': changes = dict(variable_residuals=(), constraint_residuals=(), witness=valid.witness)
    elif fault == 'objective': changes = dict(objective=.25)
    elif fault == 'evaluation': changes = dict(evaluation_error='invented')
    elif fault == 'cross_witness': changes = dict(witness=valid.witness)
    elif fault == 'cross_inputs': changes = dict(inputs=inputs(scenario(g=(.5,))))
    elif fault == 'duplicate_variable': changes = dict(snapshot=failed.snapshot+(failed.snapshot[0],))
    else:
        name, numeric = failed.snapshot[0]
        numeric = replace(numeric, **({'number': .25} if fault == 'snapshot_number' else {'float_hex': (.25).hex()}))
        changes = dict(snapshot=((name, numeric),)+failed.snapshot[1:])
    with pytest.raises(ValueError):
        replace(failed, **changes)


@pytest.mark.parametrize('tolerance', [.5, 1.])
def test_integer_tolerance_cannot_make_all_fractional_binaries_acceptable(tolerance):
    contract, model = fixture()
    model.on['s', 'shared', 0].set_value(.5, skip_validation=True)
    model.start['s', 'shared', 0].set_value(.5, skip_validation=True)
    with pytest.raises(ValueError, match='half an integer step'):
        audit(contract, model, spec=replace(SPEC, integer_feasibility_tolerance=tolerance))
    with pytest.raises(ValueError, match='half an integer step'):
        replace(audit(*fixture()), integer_tolerance=tolerance)
