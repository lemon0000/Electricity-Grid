"""Mechanical P2 request/dependency preparation; no solve or executable runner."""
from collections import Counter
from dataclasses import replace
from hashlib import sha256
import json
import re

from src import staged_rts24_development_v1 as c
from src.staged_rts24_reference_queries_v1 import reference_requests

PLAN,CLEAN,METHOD='on_time','early','full_temporal'
SHA=re.compile(r'[0-9a-f]{64}\Z')
ROLES=dict(reference_base_P0=10,reference_raw_need=1,recovery_min_meter=10,recovery_max_meter=10,
    actual_P=10,normal_contract_C=2,fault_firm_F=138,fault_raw_need=138)
ROW_KEYS=frozenset(('ordinal section hour role objective outage request_sha parent_request_sha parent_slot '
    'bound_query_sha parent_point_sha parent_economic_sha dynamic_reason evidence_kind serial_after '
    'state_after_actual_slot reference_slots phase_gate').split())
PROPOSED_LIMITS=dict(package_wall_seconds=3600,package_no_progress_seconds=65,point_wall_seconds=10,
    solver_seconds=5,fresh_wall_seconds=60,fresh_no_progress_seconds=60,tree_RSS_bytes=1024**3,
    per_process_commit_bytes=1024**3,Job_commit_bytes=2*1024**3,output_bytes=64*1024**2,
    output_files=8192,retained_member_handles=1024,threads=1,retries=0)


def digest(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _request_key(section,hour,role,outage):return section,hour,role,digest(outage)


def _expected_requests(fixture):
    expected={}
    for hour in range(-2,8):
        for q in reference_requests(fixture,PLAN,CLEAN,METHOD,hour)['requests']:
            expected[_request_key('actual',hour,q.role,c.plain(q.outages))]=(q.identity,q.anchor_id)
    for hour in (1,2):
        for q in c.hour_requests(fixture,PLAN,CLEAN,METHOD,hour)['requests']:
            if q.role in ('normal_contract_C','fault_firm_F','fault_raw_need'):
                expected[_request_key('contract',hour,q.role,c.plain(q.outages))]=(q.identity,q.anchor_id)
    c.require(len(expected)==309,'static compiler identity map differs')
    return expected


def build_schedule(fixture):
    c.require((fixture.first_hour,fixture.registration_end,fixture.observation_end)==(-2,4,8),'fixed P2 horizon differs')
    c.require((fixture.actual_hour,fixture.actual_duration)==(1,1),'fixed actual event differs')
    c.require(len(fixture.selected)==69,'fixed public contingency set differs')
    rows=[];previous_actual=None
    def add(q,section,parent=None,state_gate=None,dynamic=False,reference_slots=()):
        ordinal=len(rows)+1
        kind='child_lp_kkt' if q.objective!='economic' else 'economic_kkt' if parent is None else 'primal_point'
        row=dict(ordinal=ordinal,section=section,hour=q.hour,role=q.role,objective=q.objective,
            outage=c.plain(q.outages),request_sha=None if dynamic else q.identity,parent_request_sha=q.anchor_id,
            parent_slot=parent,bound_query_sha=None,parent_point_sha=None,parent_economic_sha=None,
            dynamic_reason='policy_power_and_parent_point' if dynamic else 'bound_parent_point' if parent else None,
            evidence_kind=kind,serial_after=ordinal-1 if ordinal>1 else None,
            state_after_actual_slot=state_gate,reference_slots=list(reference_slots),
            phase_gate='actual_finished' if section=='contract' else 'accepted_previous_hour' if state_gate else 'declared_genesis')
        rows.append(row);return ordinal
    for hour in range(-2,8):
        h=reference_requests(fixture,PLAN,CLEAN,METHOD,hour);root=len(rows)+1;references=[]
        for q in h['requests']:
            references.append(add(q,'actual',None if q.anchor_id is None else root,previous_actual))
        base=h['requests'][0]
        previous_actual=add(replace(base,role='actual_P',outages=h['actual_outage'],anchor_id=base.identity),
            'actual',root,previous_actual,True,references)
    for hour in (1,2):
        h=c.hour_requests(fixture,PLAN,CLEAN,METHOD,hour)
        normal=next(q for q in h['requests'] if q.role=='normal_contract_C')
        root=add(normal,'contract',state_gate=previous_actual)
        for outage in fixture.selected:
            for role in ('fault_firm_F','fault_raw_need'):
                q=next(q for q in h['requests'] if q.outages==outage and q.role==role)
                add(q,'contract',root,previous_actual)
    validate_schedule(rows,fixture)
    return rows


def validate_schedule(rows,fixture):
    c.require(type(rows) is list and len(rows)==319,'P2 slot count differs')
    c.require(all(type(row) is dict and set(row)==ROW_KEYS for row in rows),'slot fields differ')
    expected_requests=_expected_requests(fixture)
    c.require(Counter(r['role'] for r in rows)==Counter(ROLES),'P2 role counts differ')
    c.require(Counter(r['section'] for r in rows)==Counter(actual=41,contract=278),'P2 sections differ')
    c.require(Counter(r['evidence_kind'] for r in rows)==Counter(economic_kkt=12,child_lp_kkt=159,primal_point=148),'P2 evidence counts differ')
    c.require(sum(r['objective']=='economic' for r in rows)==160,'QP/LP split differs')
    previous=None;offset=0
    for hour in range(-2,8):
        roles=['reference_base_P0']+(['reference_raw_need'] if hour==1 else [])+['recovery_min_meter','recovery_max_meter','actual_P']
        group=rows[offset:offset+len(roles)]
        c.require([r['role'] for r in group]==roles and all(r['section']=='actual' and r['hour']==hour
            and r['state_after_actual_slot']==previous and r['phase_gate']==('declared_genesis' if previous is None else 'accepted_previous_hour')
            for r in group),'continuous actual dependency differs')
        previous=group[-1]['ordinal'];offset+=len(roles)
    c.require(offset==41,'actual prefix differs')
    expected_outages=[c.plain(o) for o in fixture.selected]
    for hour in (1,2):
        group=rows[offset:offset+139]
        c.require(group[0]['role']=='normal_contract_C' and all(r['section']=='contract' and r['hour']==hour for r in group),'contract hour grouping differs')
        for index,outage in enumerate(expected_outages):
            firm,raw=group[1+2*index:3+2*index]
            c.require(firm['role']=='fault_firm_F' and raw['role']=='fault_raw_need'
                and firm['outage']==raw['outage']==outage,'complete contingency order differs')
        offset+=139
    for ordinal,row in enumerate(rows,1):
        c.require(type(row['ordinal']) is int and row['ordinal']==ordinal and row['serial_after']==(ordinal-1 if ordinal>1 else None),'serial order differs')
        c.require(type(row['hour']) is int and (row['serial_after'] is None or type(row['serial_after']) is int),'slot scalar types differ')
        dynamic=row['role']=='actual_P'
        objective={'reference_raw_need':'min_curtailment','fault_raw_need':'min_curtailment',
            'recovery_min_meter':'min_meter','recovery_max_meter':'max_meter'}.get(row['role'],'economic')
        expected_kind='child_lp_kkt' if objective!='economic' else 'economic_kkt' if row['parent_slot'] is None else 'primal_point'
        c.require(row['objective']==objective and row['evidence_kind']==expected_kind,'objective/evidence family differs')
        c.require((row['request_sha'] is None) if dynamic else type(row['request_sha']) is str and SHA.fullmatch(row['request_sha']),'request identity differs')
        if not dynamic:
            key=_request_key(row['section'],row['hour'],row['role'],row['outage'])
            c.require(expected_requests.get(key)==(row['request_sha'],row['parent_request_sha']),'compiled request identity differs')
        else:
            outage=fixture.selected[0] if fixture.actual_hour<=row['hour']<fixture.actual_hour+fixture.actual_duration else c.Outage('normal')
            c.require(digest(row['outage'])==digest(c.plain(outage)),'dynamic actual outage differs')
        c.require(all(row[k] is None for k in ('bound_query_sha','parent_point_sha','parent_economic_sha')),'future numeric identity filled')
        parent=row['parent_slot']
        if parent is None:
            c.require(row['parent_request_sha'] is None and row['role'] in ('reference_base_P0','normal_contract_C'),'root differs')
        else:
            c.require(type(parent) is int and 0<parent<ordinal,'invalid parent edge')
            root=rows[parent-1]
            c.require(root['role']==('reference_base_P0' if row['section']=='actual' else 'normal_contract_C')
                and root['hour']==row['hour'] and root['section']==row['section']
                and root['request_sha']==row['parent_request_sha'],'parent request binding differs')
        gate=row['state_after_actual_slot']
        c.require(gate is None or type(gate) is int and 0<gate<ordinal and rows[gate-1]['role']=='actual_P','state gate differs')
        if row['section']=='contract':c.require(row['hour'] in (1,2) and gate==41 and row['phase_gate']=='actual_finished','contract phase differs')
        else:c.require(-2<=row['hour']<=7,'actual hour differs')
        refs=row['reference_slots']
        c.require(type(refs) is list and all(type(v) is int for v in refs),'reference edge types differ')
        if dynamic:
            expected=[r['ordinal'] for r in rows[:ordinal-1] if r['section']=='actual' and r['hour']==row['hour']]
            c.require(refs==expected and row['dynamic_reason']=='policy_power_and_parent_point','actual policy dependency differs')
        else:c.require(refs==[],'unexpected reference dependency')


def _metadata(fixture):
    return dict(schema='staged_rts24_p2_preparation_v1',authority='DRAFT_NONAUTHORITATIVE',
        native_authorized=False,formal_result=False,resource_admission=False,execution_supported=False,
        state='PREPARATION_ONLY',plan=PLAN,clean=CLEAN,method=METHOD,first_hour=-2,last_hour=7,
        registration_end=4,observation_end=8,
        contract_hours=[1,2],fixture_identity=fixture.source_identity,selected_contingencies=69,
        counts=dict(points=319,QP=160,LP=159,
            actual=41,contract=278,economic_kkt=12,child_lp_kkt=159,primal_point=148,
            static_request_identities=309,dynamic_actual_request_identities=10,
            successful_path_model_builds=1276,successful_path_imports=638,schedule_generation_request_objects=326,
            validation_request_objects_per_pass=316,validation_passes_for_prepare=2,full_preparation_request_objects=958),
        proposed_stop_limits=dict(PROPOSED_LIMITS),limits_are='review_proposals_not_ETA_or_resource_admission',
        dynamic_fields='actual P/request SHA and all BoundQuery/parent point/KKT SHA remain unfilled',
        stop_policy='first numeric/transport/audit/cleanup failure closes dependent work without sibling retries',
        required_before_execution=['versioned P2 controller/provider/point-worker/fresh implementation',
            'full-DAG performance and costly-failure admission','independent review of concrete implementation',
            'separate explicit native authorization'],
        later_scope=dict(single_method_full_hourly_contract_requests=1431,three_method_full_hourly_contract_requests=4273,
            DE_inputs_and_selection='OPEN',full_FX_temporal_backing='OPEN'))


def packet(fixture):
    schedule=build_schedule(fixture)
    return dict(_metadata(fixture),schedule=schedule,schedule_sha=digest(schedule))


def validate_packet(value,fixture):
    expected=_metadata(fixture)
    c.require(type(value) is dict and set(value)==set(expected)|{'schedule','schedule_sha'},'packet fields differ')
    c.require(digest({k:value[k] for k in expected})==digest(expected),'packet scope or counts differ')
    validate_schedule(value['schedule'],fixture)
    c.require(value['schedule_sha']==digest(value['schedule']),'schedule digest differs')
