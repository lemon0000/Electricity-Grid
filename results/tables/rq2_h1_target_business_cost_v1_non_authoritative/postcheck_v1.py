"""Check actual encoded anchor parameters, retained outputs and reused bytes."""
from fractions import Fraction as Q
from hashlib import sha256
import json
from pathlib import Path

import psutil
import yaml

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def pin(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def number(value):
    if type(value) is dict and set(value)=={'numerator','denominator'}:
        return Q(int(value['numerator']),int(value['denominator']))
    assert type(value) in (int,float,str)
    return Q(str(value))


def main():
    root=HERE/'cost_01'
    request,terminal=load(root/'request.json'),load(root/'terminal.json')
    assert terminal['exit_code']==0 and terminal['reason'] is None and not terminal.get('error')
    assert terminal['junit']==dict(tests=1,failures=0,errors=0,skipped=0,accepted=True)
    assert terminal['changed_sources']==terminal['observed_processes_remaining']==[]
    assert terminal['new_normal_jobs']==terminal['real_native_calls']==0
    assert all(pin(name)==expected for name,expected in request['sources_sha256'].items())
    tested={}
    for path in (root/'tested_bytes').rglob('*'):
        if path.is_file():
            original=REPO/path.relative_to(root/'tested_bytes')
            assert pin(path)==request['sources_sha256'][str(original)]
            tested[str(path)]=pin(path)
    for name,value in terminal['retained_base_json'].items():
        assert pin(name)==pin(value['copy'])==value['sha256']
    assert len(terminal['retained_base_json'])==6
    facts=[v['copy'] for k,v in terminal['retained_base_json'].items() if Path(k).name=='fact.json']
    assert len(facts)==1
    fact=load(facts[0]);assert fact==terminal['fact']
    protocol_path=REPO/'configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml'
    protocol=yaml.safe_load(protocol_path.read_bytes())
    anchor=protocol['business_anchor']
    assert fact['frozen_v2_anchor_parameters']==anchor
    field_map={'time_step_hours':'time_step_hours','recovery_efficiency':'recovery_efficiency',
        'maximum_event_duration_hours':'maximum_event_duration_hours','maximum_event_count':'episode_event_cap',
        'normalized_energy_budget':'episode_call_energy_cap','normalized_debt_limit':'normalized_debt_cap',
        'minimum_recovery_hours':'minimum_rest_hours'}
    spec_map={'minimum_event_power':'minimum_event_power','curtailment_ramp_per_hour':'curtailment_up_ramp_per_hour',
        'response_time_hours':'response_time_hours','maximum_recovery_power':'maximum_recovery_power',
        'recovery_decimal_places':'recovery_decimal_places'}
    actuals={}
    outputs={Path(name).name:value['copy'] for name,value in terminal['retained_base_json'].items()}
    for row in fact['rows']:
        h=row['hours'];assert h in (168,192)
        science_path=Path(outputs[f'h{h}_scientific.json'])
        audit_path=Path(outputs[f'h{h}_full_carry_audit.json'])
        assert science_path.stat().st_size==row['scientific_bytes'] and pin(science_path)==row['scientific_sha256']
        assert audit_path.stat().st_size==row['full_carry_bytes'] and pin(audit_path)==row['full_carry_sha256']
        science,audit=load(science_path),load(audit_path)
        spec=audit['cursor']['spec']
        envelope=dict(audit['cursor']['initial']['tracks'][0][1]['physical']['envelope'])
        assert all(number(envelope[key])==number(anchor[target]) for key,target in field_map.items())
        assert all(number(spec[key])==number(anchor[target]) for key,target in spec_map.items())
        assert number(spec['committed_capacity'])==Q(1,2)
        assert number(audit['mechanism']['alpha'])==Q(1,2)
        assert number(audit['mechanism']['flexible_fraction'])==Q(anchor['flexible_fraction'])
        assert number(audit['mechanism']['recovery_headroom_fraction'])==Q(anchor['recovery_headroom_coefficient'])
        assert number(audit['mechanism']['normalized_unit_mw'])==250
        assert len(audit['history'])==len(audit['cursor']['records'])==science['completed_actions']==h
        assert [v['relative_hour'] for v in audit['history']]==list(range(h))
        for index,(current,outcome) in enumerate(zip(science['inputs'],science['outcomes'])):
            action=outcome['action'];assert outcome['committed']
            q=number(action['grid_served'])+number(action['cfe_served'])
            r=number(action['recovery']);w=number(current['allocation']['workload'])
            assert number(action['actual_service_power'])==w-q+r
            assert q+r<=Q(1,2)
            assert q<=Q(anchor['flexible_fraction'])*w
            assert number(action['grid_served'])==(Q(17,1000) if index==167 else 0)
            assert number(action['cfe_served'])==0
            assert r==(Q(1,50) if index==191 else 0)
        cohorts=science['state']['tracks'][0]['cohorts']
        assert len(cohorts)==1 and cohorts[0]['created_hour']==168 and cohorts[0]['due_hour']==192
        assert number(cohorts[0]['incurred'])==Q(17,1000)
        assert number(cohorts[0]['remaining'])==(Q(17,1000) if h==168 else 0)
        if h==168:
            assert cohorts[0]['missed_at_deadline'] is None
        else:
            assert number(cohorts[0]['missed_at_deadline'])==0
        actuals[str(h)]=dict(actual_policy=spec,actual_envelope=envelope,actual_mechanism=audit['mechanism'],
            scientific_path=str(science_path),full_carry_path=str(audit_path),
            exact_service_balance_checked=True,
            called_power_within_available_flexibility_checked=True,
            called_plus_recovery_within_capacity_checked=True,cohort=cohorts[0])
    previous=HERE.parent/'rq2_h1_constructor_window_fault_v1_non_authoritative/final_verification.json'
    previous_receipt=load(previous)
    assert pin(previous)=='925f9370ad00f72d8cb0a3af7abdca26dcb8eb168f346ba9ac24b763232fcb20'
    assert len(previous_receipt['bindings'])==208
    assert all(pin(name)==expected for name,expected in previous_receipt['bindings'].items())
    core=load(previous_receipt['latest_core'])
    assert len(core['bindings'])==207 and pin(previous_receipt['latest_core'])==previous_receipt['latest_core_sha256']
    assert all(pin(name)==expected for name,expected in core['bindings'].items())
    case=Path('D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0')
    expected_case=load(REPO/'results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03_postcheck.json')['diagnostic_case_files_sha256']
    assert {str(p):pin(p) for p in case.rglob('*') if p.is_file()}==expected_case
    owned=load(case/'external_preclose_checkpoint.json')['saved_files_sha256']
    assert len(expected_case)==465 and len(owned)==444 and all(pin(name)==expected for name,expected in owned.items())
    remaining=[]
    for pid,created in terminal['observed_processes'].items():
        try:
            process=psutil.Process(int(pid))
            if process.create_time()==created and process.is_running():remaining.append(int(pid))
        except psutil.NoSuchProcess:pass
    assert not remaining
    result=dict(status='DRAFT_NONAUTHORITATIVE',source_pins=len(request['sources_sha256']),
        all_current_source_pins_match=True,tested_snapshots=tested,retained_base_json_count=6,
        actual_encoded_parameter_mapping_verified=True,actual_parameters=actuals,
        old_constructor_core_bindings=207,old_constructor_final_bindings=208,
        old_constructor_bindings_current_match=True,saved_case_files=465,saved_owned_files=444,
        saved_case_and_owned_sha256_unchanged=True,owned_observed_processes_remaining=remaining,
        one_history_one_cohort_observation_only=True,complete_owner_event_or_chain_bound=False,
        overall_performance_review_complete=False,resource_admission=False,formal_result=False)
    target=HERE/'postcheck_v1.json'
    expected=(json.dumps(result,indent=2)+'\n').encode('utf-8')
    if target.exists() and target.read_bytes()!=expected:
        assert target.read_bytes()==(HERE/'preseal_before_contract_fix'/target.name).read_bytes()
    target.write_bytes(expected)
    print(json.dumps(dict(source_pins=result['source_pins'],tested_snapshots=len(tested),
        actual_anchor_verified=True,retained_files=6,prior_core_final=[207,208],saved_files=465,owned_files=444)))


if __name__=='__main__':main()
