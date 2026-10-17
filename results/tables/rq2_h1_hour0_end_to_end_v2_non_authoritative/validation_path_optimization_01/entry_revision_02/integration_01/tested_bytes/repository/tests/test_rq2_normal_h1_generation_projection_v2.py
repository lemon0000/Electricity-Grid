from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from math import nextafter, inf
from pathlib import Path
import sqlite3

import pytest
from pyomo.environ import Var, value

from tests.test_rq2_continuous_grid_normal_v1 import fixture, assignment_for
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver, saved, packet, spec
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_generation_projection_v2 as api
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_hour_replay_v2 as replay
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_hour_replay as legacy
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_hour_archive_v2 as archive


def zero_case(locks=(0.,)):
    inputs = fixture(1, committed=False, age=3, demand=0.)
    assignment = assignment_for(inputs, (False,))
    request = api.model_api.H1StageRequest(inputs, locks)
    return request, assignment


def project(request, assignment):
    pin = api.model_api.h1_stage_identity(request)
    model = api.model_api.build_h1_stage_model(request, expected_identity=pin)
    for variable in model.component_data_objects(Var):
        variable.set_value(assignment[variable.name], skip_validation=True)
    return api.project_and_audit(request, assignment, expected_identity=pin,
                               raw_objective_hex=float(value(model.objective)).hex())


@pytest.mark.parametrize('amount', [-1e-9, -1e-12, nextafter(0., -inf)])
def test_authorized_closed_left_open_right_interval_and_immutable_raw(amount):
    req, assignment = zero_case()
    assignment['generation[normal,0,G1]'] = amount
    before = deepcopy(assignment)
    candidate, audit, receipt = project(req, assignment)
    assert assignment == before
    assert candidate['generation[normal,0,G1]'].hex() == '0x0.0p+0'
    assert receipt['changes'] == [['generation[normal,0,G1]', amount.hex(), '0x0.0p+0', (-amount).hex()]]
    assert receipt['candidate_accepted'] and not audit.errors
    assert receipt['maximum_power_balance_residual'] == 0
    assert receipt['raw_assignment_identity'] != receipt['candidate_assignment_identity']


def test_outside_threshold_is_rejected():
    req, assignment = zero_case()
    assignment['generation[normal,0,G1]'] = nextafter(-1e-9, -inf)
    with pytest.raises(ValueError): project(req, assignment)


@pytest.mark.parametrize('amount', [-0.0, 0.0])
def test_zero_sign_and_unrelated_continuous_values_are_preserved(amount):
    req, assignment = zero_case()
    assignment['generation[normal,0,G1]'] = amount
    assignment['branch_flow[normal,0,AC1]'] = -1e-12
    candidate, _, receipt = project(req, assignment)
    assert not receipt['changes'] and not receipt['normalization_applied']
    assert {k:float(v).hex() for k,v in candidate.items()} == {k:float(v).hex() for k,v in assignment.items()}


def test_positive_off_unit_generation_is_not_authorized():
    req, assignment = zero_case()
    assignment['generation[normal,0,G1]'] = 1e-12
    candidate, audit, receipt = project(req, assignment)
    legacy_audit = api.model_api.audit_h1_assignment(req, assignment,
        expected_identity=api.model_api.h1_stage_identity(req))
    assert audit == legacy_audit and not receipt['changes']
    assert candidate['generation[normal,0,G1]'].hex() == (1e-12).hex()
    assert assignment['generation[normal,0,G1]'] == 1e-12


@pytest.mark.parametrize('name', ['generation[outage,0,G1]', 'generation[normal,1,G1]'])
def test_noncanonical_generation_keys_are_not_mapped(name):
    req, assignment = zero_case()
    assignment[name] = -1e-12
    with pytest.raises(ValueError, match='complete H1 assignment'): project(req, assignment)


def test_original_generation_objective_hex_must_not_change():
    req, assignment = zero_case((0.,0.))
    assignment['generation[normal,0,G1]'] = -1e-12
    with pytest.raises(api.ProjectionRejected) as error: project(req, assignment)
    assert error.value.receipt['changes'] and not error.value.receipt['candidate_accepted']
    assert error.value.receipt['raw_objective_hex'] == (-1e-12).hex()


def test_raw_lock_failure_cannot_be_repaired():
    req, assignment = zero_case((1e-8,))
    assignment['generation[normal,0,G1]'] = -1e-12
    with pytest.raises(ValueError, match='non-domain'): project(req, assignment)


def test_drifted_threshold_rejected(monkeypatch):
    req, assignment = zero_case()
    monkeypatch.setattr(api, 'EPSILON', 1e-6)
    with pytest.raises(ValueError, match='epsilon drift'): project(req, assignment)


def test_complete_saved_chain_gets_distinct_successor_projection(saved):
    p = packet()
    limits = replay.H1HourReplayLimits(3,100,500)
    result = replay.replay_stream(p,spec(),limits,iter(saved[1]),expected_key=replay.request_key(p,spec(),limits))
    old_limits = legacy.H1HourReplayLimits(3,100,500)
    old = legacy.replay_stream(p,spec(),old_limits,iter(saved[1]),expected_key=legacy.request_key(p,spec(),old_limits))
    assert result.projection_identity != old.projection_identity
    assert result.canonical_locks == old.canonical_locks
    assert result.report_sha256 == old.report_sha256
    assert json.loads(result.projection_payload)['units'] == json.loads(old.projection_payload)['units']
    assert not result.formal_result and result.solver_calls_by_replay == 0


def test_saved_native_rejection_is_successor_candidate_only():
    from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_job as old_job
    root = Path(__file__).resolve().parents[1]/'results/tables/rq2_normal_h1_origin_calibration_v1_non_authoritative'
    request = json.loads((root/'request.json').read_bytes())
    packet_value = old_job._packet(request)
    database = root/'collector_non_authoritative/stages_non_authoritative/h1_chunk_journal.sqlite3'
    before = sha256(database.read_bytes()).hexdigest()
    connection = sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1',uri=True)
    try:
        metadata = [json.loads(row[0]) for row in connection.execute('select metadata from events order by seq')]
        locks = tuple(float.fromhex(m['lock_hex']) for m in metadata if m['kind']=='stage_accepted')
        raw = b''.join(row[0] for row in connection.execute('select payload from chunks where event_seq=26 order by chunk_index'))
    finally: connection.close()
    assert sha256(raw).hexdigest() == '81f70cbec441329bd80c99687a1a77d762942fbf7f807350ff164cf169945599'
    with pytest.raises(legacy.H1ReportAuditRejected):
        legacy._audit_stage(packet_value,old_job._configuration(request)[0].specification,
                            legacy.H1HourReplayLimits(232,891,1211),25,locks,raw)
    result = replay._audit_stage(packet_value,old_job._configuration(request)[0].specification,
                                replay.H1HourReplayLimits(232,891,1211),25,locks,raw)
    receipt = result['generation_mapping']
    assert receipt['changes'] == [['generation[normal,0,201_CT_2]', '-0x1.7bd24a3baa1f4p-39', '0x0.0p+0', '0x1.7bd24a3baa1f4p-39']]
    assert receipt['candidate_audit']['errors'] == ()
    assert receipt['raw_objective_hex'] == '-0x0.0p+0'
    assert result['assignment']['generation[normal,0,201_CT_2]'] == 0
    assert sha256(database.read_bytes()).hexdigest() == before
    assert json.loads((root/'worker_result.json').read_bytes())['summary']['status']=='rejected'


@pytest.mark.parametrize('field', ['candidate_assignment_identity','rule_identity','changes'])
def test_mapping_receipt_tampering_rejected_on_fresh_reopen(tmp_path,saved,field,monkeypatch):
    limits = replay.H1HourReplayLimits(3,100,500)
    root = tmp_path/'archive_non_authoritative'
    owner = archive.DevelopmentH1HourArchive(root,packet(),spec(),limits,
        parent_intent_head='1'*64,source_lineage_identity='2'*64,create=True)
    original = owner._stage_metadata
    def tampered(*args):
        meta = deepcopy(original(*args))
        meta['generation_mapping'][field] = ([['forged','-0x1p-50','0x0p+0','0x1p-50']]
            if field == 'changes' else '9'*64)
        return meta
    monkeypatch.setattr(owner,'_stage_metadata',tampered)
    try:
        owner.record_report(saved[1][0],expected_head=owner.head)
        head = owner.head
    finally: owner.close()
    with pytest.raises(ValueError, match='metadata differs from raw reconstruction'):
        archive.DevelopmentH1HourArchive(root,packet(),spec(),limits,
            parent_intent_head='1'*64,source_lineage_identity='2'*64,expected_head=head)


def multi_case(count=2, locks=(0.,)):
    data = fixture(1,committed=False,age=3,demand=0.).data
    units = tuple(replace(data.generators[0],uid=f'G{i}',p_min_mw=0.,
        cost_breakpoints_mw=(0.,30.,60.,100.),cost_values_usd_per_hour=(0.,30.,60.,100.))
        for i in range(1,count+1))
    row = replace(data.hourly_points[0],generator_min_mw={g.uid:0. for g in units},
                  generator_max_mw={g.uid:100. for g in units})
    p = packet(data=replace(data,generators=units,hourly_points=(row,)))
    req = api.model_api.H1StageRequest(p.inputs,locks)
    model = api.model_api.build_h1_stage_model(req,expected_identity=api.model_api.h1_stage_identity(req))
    assignment = {v.name:float(value(v)) if v.fixed else 0. for v in model.component_data_objects(Var)}
    return req, assignment


def test_multiple_deltas_are_sorted_and_do_not_mutate_raw():
    req, assignment = multi_case()
    assignment['generation[normal,0,G2]']=-2e-12
    assignment['generation[normal,0,G1]']=-1e-12
    original=deepcopy(assignment)
    candidate, audit, receipt=project(req,dict(reversed(list(assignment.items()))))
    assert assignment==original and not audit.errors
    assert [row[0] for row in receipt['changes']]==['generation[normal,0,G1]','generation[normal,0,G2]']
    assert all(candidate[row[0]]==0 for row in receipt['changes'])


def test_mapping_that_breaks_power_balance_is_rejected_with_receipt():
    req, assignment = multi_case(3,locks=())
    assignment.update({'generation[normal,0,G1]':-7.5e-10,
        'generation[normal,0,G2]':-7.5e-10,'generation[normal,0,G3]':1.5e-9,
        'commitment[0,G3]':1.,'startup[0,G3]':1.,'segment_power[0,G3,0]':1.5e-9})
    with pytest.raises(api.ProjectionRejected) as error: project(req,assignment)
    receipt=error.value.receipt
    assert receipt['maximum_power_balance_residual']>1e-9
    assert receipt['changes'] and not receipt['candidate_accepted']
