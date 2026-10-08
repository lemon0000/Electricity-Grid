from dataclasses import replace

import pytest
from pyomo.environ import Var

from test_rq2_outage_trajectory_v1 import normal_base, flexible_base, inputs, build, assign
from src.rq2_joint_deliverability_boundary_v1.outage_trajectory import outage_trajectory_identity
from src.rq2_joint_deliverability_boundary_v1.outage_assignment import (
    OutageAssignmentWitness, OutageReplayCarry, audit_outage_assignment, replay_outage_chunk)


def assignment(contract, trajectory=((20., 20.), (0., 40.), (20., 20.))):
    model = build(contract)
    assign(model, trajectory)
    return {v.name: v.value for v in model.component_data_objects(Var)}


def audit(contract, values=None):
    return audit_outage_assignment(contract, assignment(contract) if values is None else values,
        expected_identity=outage_trajectory_identity(contract))


def replay(contract, witness, hours, before=None):
    return replay_outage_chunk(contract, witness, hours,
        expected_identity=outage_trajectory_identity(contract), before=before)


def test_complete_canonical_assignment_and_both_cut_edges(normal_base):
    contract = inputs(normal_base)
    witness = audit(contract)
    assert witness.errors == ()
    assert witness.maximum_fixed_violation == witness.maximum_bound_violation == 0.
    assert witness.maximum_constraint_violation == witness.objective_value == 0.
    complete = replay(contract, witness, (1, 2, 3))
    for cut in (1, 2):
        prefix = replay(contract, witness, tuple(range(1, cut + 1)))
        assert replay(contract, witness, tuple(range(cut + 1, 4)), prefix) == complete
    outage = replay(contract, witness, (1, 2))
    assert outage.active_event == contract.events[0]
    assert outage.availability == (('G1', False), ('G2', True))
    assert outage.generation_mw == (('G1', 0.), ('G2', 40.))
    assert outage.normal_carry.points[0].generation_mw == 20.
    assert complete.active_event is None
    assert complete.normal_carry.elapsed_state_hours == (4, 4)


def test_actual_terminal_does_not_reset_to_normal(flexible_base):
    witness = audit(flexible_base, assignment(flexible_base, ((25., 25.), (0., 50.), (25., 25.))))
    assert not witness.errors
    terminal = replay(flexible_base, witness, (1, 2, 3))
    assert terminal.generation_mw == (('G1', 25.), ('G2', 25.))
    assert terminal.normal_carry.points[0].generation_mw == pytest.approx(30.)


@pytest.mark.parametrize('variable,number,error', [
    ('angle_degrees[0,1]', 1., 'fixed'),
    ('generation[1,G1]', 1., 'bound'),
    ('generation[0,G2]', 21., 'constraint'),
    ('branch_flow[1,AC1]', 101., 'bound'),
    ('dc_flow[1,DC1]', 101., 'bound')])
def test_invalid_assignment_cannot_handoff(normal_base, variable, number, error):
    contract = inputs(normal_base)
    values = assignment(contract)
    values[variable] = number
    witness = audit(contract, values)
    assert 'canonical_outage_' + error + '_violation' in witness.errors
    with pytest.raises(ValueError, match='accepted current'):
        replay(contract, witness, (1,))


@pytest.mark.parametrize('bad', [True, None, float('nan'), float('inf'), '20'])
def test_nonfinite_and_coerced_assignment_rejected(normal_base, bad):
    contract = inputs(normal_base)
    values = assignment(contract)
    values['generation[0,G1]'] = bad
    with pytest.raises(ValueError, match='finite built-in'):
        audit(contract, values)


@pytest.mark.parametrize('extra', [False, True])
def test_variable_inventory_is_exact(normal_base, extra):
    contract = inputs(normal_base)
    values = assignment(contract)
    if extra:
        values['unregistered'] = 0.
    else:
        values.pop('angle_degrees[1,2]')
    with pytest.raises(ValueError, match='inventory'):
        audit(contract, values)


@pytest.mark.parametrize('hours', [(), (2,), (1, 3), (1, 2, 3, 4), (True,), [1]])
def test_invalid_source_slice_rejected(normal_base, hours):
    contract = inputs(normal_base)
    with pytest.raises(ValueError):
        replay(contract, audit(contract), hours)


def test_witness_and_carry_no_public_relabel(normal_base):
    contract = inputs(normal_base)
    witness = audit(contract)
    carry = replay(contract, witness, (1,))
    for kind in (OutageAssignmentWitness, OutageReplayCarry):
        with pytest.raises(TypeError):
            kind()
    with pytest.raises(TypeError):
        replace(witness, errors=())
    with pytest.raises(TypeError):
        replace(carry, source_hour=2)


def test_carry_cannot_switch_full_assignment_even_with_same_normal(flexible_base):
    first = audit(flexible_base, assignment(flexible_base, ((25., 25.), (0., 50.), (25., 25.))))
    second = audit(flexible_base, assignment(flexible_base, ((24., 26.), (0., 50.), (25., 25.))))
    assert not first.errors and not second.errors
    assert first.result_id != second.result_id
    carry = replay(flexible_base, first, (1,))
    with pytest.raises(ValueError, match='full assignment prefix'):
        replay(flexible_base, second, (2, 3), carry)


def test_stale_problem_and_normal_carry_rejected(normal_base):
    contract = inputs(normal_base)
    witness = audit(contract)
    changed = replace(contract, curtailment_weights=(1., 2., 1.))
    with pytest.raises(ValueError, match='accepted current'):
        replay(changed, witness, (1,))
    with pytest.raises(ValueError, match='actual carry'):
        replay(contract, witness, (2,), contract.normal_inputs.carry)


def test_canonical_rebuild_ignores_mutated_caller_model(normal_base):
    contract = inputs(normal_base)
    model = build(contract)
    assign(model, ((20., 20.), (0., 40.), (20., 20.)))
    model.balance.deactivate()
    model.generation[0, 'G2'].set_value(21.)
    witness = audit(contract, {v.name: v.value for v in model.component_data_objects(Var)})
    assert 'canonical_outage_constraint_violation' in witness.errors


def test_original_assignment_owned_and_bound(normal_base):
    contract = inputs(normal_base)
    values = assignment(contract)
    witness = audit(contract, values)
    identity = witness.result_id
    values['generation[0,G2]'] = 79.
    assert witness.result_id == identity
    assert not replay(contract, witness, (1,)).active_event


def test_continuing_outage_slice_keeps_active_original_event(normal_base):
    contract = inputs(normal_base)
    contract = replace(contract, events=(replace(contract.events[0], start_hour=0),),
        actual_origin=replace(contract.actual_origin, generation_mw=(('G1', 0.), ('G2', 40.)),
            availability=(('G1', False), ('G2', True))))
    witness = audit(contract, assignment(contract, ((0., 40.), (0., 40.), (20., 20.))))
    assert not witness.errors
    one = replay(contract, witness, (1,))
    two = replay(contract, witness, (2,), one)
    assert one.active_event == two.active_event == contract.events[0]
    assert replay(contract, witness, (3,), two) == replay(contract, witness, (1, 2, 3))


def test_adjacent_generator_repair_and_branch_trip_keep_distinct_events(normal_base):
    from src.scenarios.rts_gmlc_n1_chronology import N1OutageEvent
    contract = inputs(normal_base)
    contract = replace(contract, events=(*contract.events, N1OutageEvent(1, 'next', 'branch', 'AC1', 2, 3)))
    witness = audit(contract)
    prefix = replay(contract, witness, (1, 2))
    terminal = replay(contract, witness, (3,), prefix)
    assert prefix.active_event == contract.events[0]
    assert terminal.active_event == contract.events[1]
    assert terminal.availability == (('G1', True), ('G2', True))
    assert terminal == replay(contract, witness, (1, 2, 3))


def test_fixed_vector_and_reference_angles_are_checked_separately(normal_base):
    contract = inputs(normal_base, mode='fixed_curtailment_vector')
    values = assignment(contract)
    values['curtailment[1]'] = 1.
    witness = audit(contract, values)
    assert witness.maximum_fixed_violation == 1.
    assert 'canonical_outage_fixed_violation' in witness.errors
    values = assignment(contract)
    values['angle_degrees[0,1]'] = values['angle_degrees[0,2]'] = 1.
    witness = audit(contract, values)
    assert witness.maximum_constraint_violation == 0.
    assert witness.maximum_fixed_violation == 1.


def test_finite_inputs_with_overflow_do_not_create_accepted_identity(normal_base):
    contract = inputs(normal_base)
    values = assignment(contract)
    values['generation[0,G1]'] = values['generation[0,G2]'] = 1e308
    witness = audit(contract, values)
    assert witness.maximum_constraint_violation is None
    assert witness.errors
    assert len(witness.result_id) == 64
    with pytest.raises(ValueError, match='accepted current'):
        replay(contract, witness, (1,))


def test_auditor_source_drift_invalidates_witness(normal_base, monkeypatch, tmp_path):
    import src.rq2_joint_deliverability_boundary_v1.outage_assignment as module
    contract = inputs(normal_base)
    witness = audit(contract)
    other = tmp_path / 'changed_auditor.py'
    other.write_text('changed implementation', encoding='utf8')
    monkeypatch.setattr(module, '__file__', str(other))
    with pytest.raises(ValueError, match='accepted current'):
        replay(contract, witness, (1,))


def test_fresh_import_closure_is_identity_bound():
    import json
    from pathlib import Path
    import subprocess
    import sys
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import SOURCE_DEPENDENCIES
    from src.rq2_joint_deliverability_boundary_v1.continuous_grid_candidate import EXTRA_DEPENDENCIES
    script = '''
import json, sys
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.outage_assignment
root = Path.cwd()
print(json.dumps(sorted(Path(module.__file__).resolve().relative_to(root).as_posix()
    for name, module in sys.modules.items() if name == 'src' or name.startswith('src.'))))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script], check=True, capture_output=True,
        text=True, cwd=Path(__file__).resolve().parents[1], timeout=30)
    expected = set(SOURCE_DEPENDENCIES) | set(EXTRA_DEPENDENCIES) | {
        'src/rq2_joint_deliverability_boundary_v1/outage_trajectory.py',
        'src/rq2_joint_deliverability_boundary_v1/outage_assignment.py'}
    assert set(json.loads(result.stdout)) == expected


@pytest.mark.parametrize('field,changed', [('CONTRACT', 'changed'), ('TOLERANCE', 2e-6)])
def test_runtime_audit_contract_drift_rejected_and_existing_identity_stable(normal_base, monkeypatch, field, changed):
    import src.rq2_joint_deliverability_boundary_v1.outage_assignment as module
    contract = inputs(normal_base)
    witness = audit(contract)
    identity = witness.result_id
    near = assignment(contract)
    near['branch_flow[1,AC1]'] += 1.1e-6
    assert 'canonical_outage_constraint_violation' in audit(contract, near).errors
    monkeypatch.setattr(module, field, changed)
    assert witness.result_id == identity
    with pytest.raises(ValueError, match='contract or tolerance drift'):
        audit(contract, near)
    with pytest.raises(ValueError, match='contract or tolerance drift'):
        replay(contract, witness, (1,))
