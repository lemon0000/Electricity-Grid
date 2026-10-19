from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('resource_gap_audit',
    ROOT/'experiments/audit_rq2_h1_resource_readiness_v1.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


@pytest.fixture
def inputs():
    return (yaml.safe_load((ROOT/'configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml').read_bytes()),
        json.loads((ROOT/'results/tables/rq2_finite_enrollment_support_v1_non_authoritative/coverage_168_24_verified.json').read_bytes()))


def test_full_support_and_missing_tail_are_preserved(inputs):
    result = api.protocol_counts(*inputs)
    assert (result['theta_count'], result['alpha_count'], result['cell_count']) == (19,100,1900)
    assert result['capacity_probe_count'] == 101
    assert result['maximum_hours_per_pair'] == 192
    training = result['splits']['training']
    assert training['cell_pair_identities'] == 27823600
    assert training['four_arm_object_identities'] == 111294400
    assert training['pairs_per_cell'] == 14644
    assert training['pairs_with_missing_followup_retained'] == 604
    assert result['splits']['holdout']['pairs_with_missing_followup_retained'] == 593
    assert not result['identity_count_is_required_solver_call_count']


@pytest.mark.parametrize('mutation', ['unapproved','old_cells','drop_tail','duplicate_window','split_move','tail_flag','tail_length','oat_anchor','repeat_factor'])
def test_reject_contract_and_source_corruption(inputs, mutation):
    p,c = deepcopy(inputs)
    if mutation=='unapproved': p['scientific_parameters_approved']=False
    elif mutation=='old_cells': p['design']['expected_cell_count']=46
    elif mutation=='drop_tail': c['windows']=[r for r in c['windows'] if r['followup_source_complete']]
    elif mutation=='duplicate_window': c['windows'].append(deepcopy(c['windows'][0]))
    elif mutation=='split_move': c['windows'][0]['split']='training'
    elif mutation=='tail_flag': c['windows'][0]['followup_source_complete']=False
    elif mutation=='tail_length': c['windows'][0]['missing_followup_hours']=1
    elif mutation=='oat_anchor': p['design']['oat_non_anchor']['recovery_efficiency'].append('0.85')
    elif mutation=='repeat_factor': p['design']['primary_factorial']['flexible_fraction'].append('0.20')
    with pytest.raises(ValueError): api.protocol_counts(p,c)


@pytest.mark.parametrize('grid,denominator', [({'first':True,'last':100,'step':1},100),
    ({'first':1,'last':100,'step':1},100),({'first':0,'last':99,'step':1},100),
    ({'first':0,'last':100,'step':3},100),({'first':0,'last':101,'step':1},100),
    ({'first':0,'last':100,'step':0},100),({'first':0,'last':100,'step':1},True)])
def test_exact_grid_rejects_ambiguous_endpoints_and_types(grid, denominator):
    with pytest.raises(ValueError): api.grid_count(grid,denominator,include_zero=True)


def test_no_implicit_probe_multiplier_or_resource_admission(inputs):
    counts = api.protocol_counts(*inputs)
    report = api.normal_scenarios(counts,stages=232,content_per_pair=774088294400,hourly_task_seconds=3600)
    first, common, repeat = report['rows'][:3]
    assert first['normal_solver_slots'] == 44544
    assert first['independent_hour_job_wall_allowance_seconds'] == 691200
    assert common['normal_solver_slots'] == 652302336
    assert repeat['normal_solver_slots'] == 1239374438400
    assert common['reuse_verification_required'] is True
    assert common['normal_solver_slots']*1900 == repeat['normal_solver_slots']
    assert report['complete_study_solver_calls'] is None
    assert report['complete_study_task_manifest'] is None
    assert all(r['predicted_elapsed_seconds'] is None and r['actual_execution_count'] is None
               and r['admitted'] is False for r in report['rows'])


def test_pins_reject_changed_evidence_before_counting(tmp_path, monkeypatch):
    monkeypatch.setattr(api,'ROOT',tmp_path)
    p=tmp_path/'evidence.json';p.write_text('{"changed":true}',encoding='ascii')
    monkeypatch.setattr(api,'PINS',{'evidence.json':'0'*64})
    with pytest.raises(ValueError,match='pinned evidence drift'): api.pinned_inputs()


def test_factorized_catalog_has_every_probe_and_keeps_holdout_conditional(inputs):
    p,c=inputs
    catalog=api.obligation_catalog(p,c,api.protocol_counts(p,c))
    assert api.REPORT_SCHEMA=='h1_resource_readiness_gap_audit_v2'
    assert catalog['schema']=='factorized_capacity_obligation_catalog_v2'
    assert catalog['identity_counts']=={'training_lb':111294400,'training_ub':11240734400,
        'training_b6_actual':27823600,'holdout':108953600}
    lb=api.obligation_at(catalog,'training_lb',111294399)
    assert 'capacity' not in lb['coordinate']
    first=api.obligation_at(catalog,'training_ub',0)
    assert first['coordinate']['capacity']=='0'
    last=api.obligation_at(catalog,'training_ub',11240734399)
    assert last['coordinate']['capacity']=='1'
    assert last['coordinate']['alpha']=='1' and last['coordinate']['arm']=='joint-B6'
    assert api.obligation_at(catalog,'training_ub',1)['coordinate']['capacity']=='1/100'
    assert api.obligation_at(catalog,'training_ub',100)['coordinate']['capacity']=='1'
    next_arm=api.obligation_at(catalog,'training_ub',101)['coordinate']
    assert next_arm['arm']=='CFE-only' and next_arm['capacity']=='0'
    next_alpha=api.obligation_at(catalog,'training_ub',14644*4*101)['coordinate']
    assert next_alpha['alpha']=='1/50' and next_alpha['arm']=='network-only'
    next_theta=api.obligation_at(catalog,'training_ub',100*14644*4*101)['coordinate']
    assert next_theta['alpha']=='1/100' and next_theta['theta']!=first['coordinate']['theta']
    actual=api.obligation_at(catalog,'training_b6_actual',27823599)
    assert actual['coordinate']['arm']=='joint-B6' and 'capacity' not in actual['coordinate']
    assert actual['frozen_training_ub'] is None and actual['solver_task_id'] is None
    holdout=api.obligation_at(catalog,'holdout',108953599)
    assert 'capacity' not in holdout['coordinate'] and 'proof' not in holdout['coordinate']
    assert holdout['frozen_training_ub'] is None and holdout['solver_task_id'] is None
    assert not catalog['verified_reuse_edges'] and not catalog['analytic_exclusion_proofs']
    assert not catalog['complete_executable_task_inventory']
    assert all(count is None for count in catalog['eligible_execution_counts'].values())


@pytest.mark.parametrize('split,ordinal',[('training_lb',True),('training_ub',-1),('training_lb',111294400),
    ('training_ub',11240734400),('training_b6_actual',27823600),('holdout',108953600),('combined',0)])
def test_catalog_random_access_rejects_invalid_coordinate(inputs,split,ordinal):
    p,c=inputs;catalog=api.obligation_catalog(p,c,api.protocol_counts(p,c))
    with pytest.raises(ValueError):api.obligation_at(catalog,split,ordinal)
