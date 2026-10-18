import json
from fractions import Fraction as Q

import pytest

from experiments import export_rq2_continuous_composite_diagnostics_v1 as delivery
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import B6,JOINT


@pytest.fixture(scope='module')
def payload():
    return delivery.build_payload()


def rows(payload):
    return [json.loads(line) for line in payload['records.jsonl'].splitlines()]


def rational(value):
    return Q(int(value['numerator']),int(value['denominator']))


def test_counts_and_transition_are_not_double_counted(payload):
    summary={(r['case_id'],r['arm_id']):r for r in json.loads(payload['summary.json'])}
    assert len(summary)==32
    result=summary['b6_shared_rejection',B6]
    assert (result['primary_accepted_hours'],result['recovery_validated_hours'],result['validated_unique_hours'])==(25,23,48)
    assert result['submitted_unique_hours']==48 and result['original_rejection_submission_index']==26
    records=rows(payload)
    assert len(records)==1330
    assert sum(r['outcome']=='unassessed' for r in records)==6
    selected=[r for r in records if (r['case_id'],r['arm_id'])==('b6_shared_rejection',B6)]
    transition=selected[25]
    assert transition['primary_event']['status']=='rejected_uncommitted'
    assert transition['primary_event']['planned_candidate'] is not None
    assert transition['recovery_event']['actual_status']=='assumed_action_validated'
    assert transition['outcome']=='recovery_validated'
    assert all(r['primary_event'] is None for r in selected[26:])
    assert selected[-1]['primary_planning_archive']==transition['primary_planning_archive']


def test_independent_hourly_power_debt_balance_and_unassessed_state(payload):
    for row in rows(payload):
        before=row['before_execution']['tracks']['shared']
        after=row['committed_execution']['tracks']['shared']
        if row['outcome']=='unassessed':
            assert before==after
            continue
        if row['outcome']=='recovery_validated':
            action=row['recovery_event']['action']
        else:
            action=row['primary_event']['accepted_actions']['shared']['physical']
        h=row['observation']['hour']
        g=0 if row['arm_id']==delivery.prefix.CFE else Q(str(h['grid_request']))
        c=0 if row['arm_id']==delivery.prefix.NETWORK else Q(str(h['cfe_request']))
        r=Q(str(action['recovery']))
        assert Q(str(action['actual_service_power']))==Q(str(h['workload_occupancy']))-g-c+r
        old=sum((rational(v['remaining']) for v in before['ledger']['cohorts']),Q(0))
        new=sum((rational(v['remaining']) for v in after['ledger']['cohorts']),Q(0))
        assert new==old+g+c-Q('.8')*r


def test_raw_gap_and_hard_failure_keep_correct_last_validated_hour(payload):
    summary={(r['case_id'],r['arm_id']):r for r in json.loads(payload['summary.json'])}
    for case in ('recovery_then_hard_call','recovery_then_source_gap'):
        result=summary[case,B6]
        assert result['last_validated_hour']==28 and result['first_unassessed_submission_index']==29
        assert result['unsubmitted_input_count']==19
        assert result['actual_unassessed_hour_and_suffix_outcome'] is None
    gap=summary['recovery_then_source_gap',B6]
    assert gap['first_unassessed_source_hour']==99 and gap['unassessed_stage']=='input_validation'
    hard=summary['recovery_then_hard_call',B6]
    assert hard['first_unassessed_source_hour']==29 and hard['unassessed_stage']=='actual_validation'
    for arm in delivery.prefix.ARMS:
        result=summary['recovery_then_source_gap',arm]
        assert 'original_rejection_hour' not in result
        if arm!=B6:
            assert result['original_rejection_submission_index']==29
            assert result['original_rejection_raw_source_hour']==99
    assert all('original_rejection_hour' not in row['prefix_summary'] for row in rows(payload))


def test_evidence_policy_ids_unknown_and_censoring_survive(payload):
    inputs=[json.loads(line) for line in payload['inputs.jsonl'].splitlines()]
    assert len(inputs)==361 and all(r['evidence_class']=='mechanism_assumption' for r in inputs)
    policies=json.loads(payload['policies.json'])
    assert len(policies)==4 and all(row['policy_id'] in policies for row in rows(payload))
    summary={(r['case_id'],r['arm_id']):r for r in json.loads(payload['summary.json'])}
    unknown=summary['unknown_deadline',JOINT]
    assert all(s[2]=='deadline_unidentified' for s in unknown['cohort_statuses'])
    censored=summary['censored_prefix',JOINT]
    assert all(s[2]=='right_censored_before_deadline' for s in censored['cohort_statuses'])
    evidence=json.loads(payload['evidence.json'])
    assert evidence['real_observations_used'] is False and evidence['risk_probability'] is None
    config=json.loads(payload['config.json'])
    scenario=config['scenarios']
    original=dict(scenario,cases=scenario['cases'][:6])
    legacy=delivery.prefix.make_inputs(original)
    assert [{k:v for k,v in r.items() if k!='input_role'} for r in inputs[:265]]==legacy


def put_package(path,payload):
    path.mkdir()
    for name,data in payload.items():
        (path/name).write_bytes(data)
    (path/'diagnostic_manifest.json').write_bytes(delivery.prefix.encoded(delivery.manifest(payload)))


def test_create_verify_and_refuse_overwrite(tmp_path):
    path=tmp_path/'package_non_authoritative'
    result=delivery.write_package(path)
    assert result['record_count']==1330 and result['replay_matches']
    before={p.name:p.read_bytes() for p in path.iterdir()}
    with pytest.raises(FileExistsError):
        delivery.write_package(path)
    assert before=={p.name:p.read_bytes() for p in path.iterdir()}
    assert delivery.verify_package(path)==result


@pytest.mark.parametrize('name',['records.jsonl','summary.json','policies.json','inputs.jsonl'])
def test_rehashed_output_tampering_still_fails_replay(tmp_path,payload,name):
    altered=dict(payload)
    if name=='records.jsonl':
        r=rows(payload)
        r[0]['committed_execution']['tracks']['shared']['physical']['state']['event_count']=99
        altered[name]=b''.join(map(delivery.prefix.encoded,r))
    elif name=='inputs.jsonl':
        r=[json.loads(line) for line in payload[name].splitlines()]
        r[0]['observation']['limits']['call_limit']=.123
        altered[name]=b''.join(map(delivery.prefix.encoded,r))
    elif name=='summary.json':
        r=json.loads(payload[name]); r[0]['validated_unique_hours']=999
        altered[name]=delivery.prefix.encoded(r)
    else:
        altered[name]=b'{}\n'
    path=tmp_path/'package_non_authoritative'
    put_package(path,altered)
    with pytest.raises(ValueError,match='replay mismatch'):
        delivery.verify_package(path)


@pytest.mark.parametrize('fault',['missing_manifest','extra_file','file_hash','dependency'])
def test_inventory_partial_package_and_dependency_faults(tmp_path,payload,fault):
    path=tmp_path/'package_non_authoritative'
    put_package(path,payload)
    if fault=='missing_manifest':
        (path/'diagnostic_manifest.json').unlink()
    elif fault=='extra_file':
        (path/'unexpected').write_text('x')
    elif fault=='file_hash':
        (path/'summary.json').write_text('[]')
    else:
        inventory=json.loads((path/'diagnostic_manifest.json').read_bytes())
        inventory['dependencies'][delivery.CONTROLLER]='0'*64
        (path/'diagnostic_manifest.json').write_bytes(delivery.prefix.encoded(inventory))
    with pytest.raises(ValueError,match='mismatch'):
        delivery.verify_package(path)
