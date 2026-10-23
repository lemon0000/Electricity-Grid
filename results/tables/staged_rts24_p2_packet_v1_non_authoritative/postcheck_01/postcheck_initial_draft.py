"""Independent saved metadata/edge/byte arithmetic; no research imports or replay."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import stat

ROOT=Path(__file__).resolve().parents[4]
BASE=Path(__file__).resolve().parent.parent
POST=BASE/'postcheck_01'
PACK=BASE/'packet_01'
CHECKS=BASE/'development_checks_01'
P1=ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
PRIOR=P1.parent/'p1_execution_review_01/postcheck_03.stdout.json'
ROW_KEYS=set(('ordinal section hour role objective outage request_sha parent_request_sha parent_slot '
    'bound_query_sha parent_point_sha parent_economic_sha dynamic_reason evidence_kind serial_after '
    'state_after_actual_slot reference_slots phase_gate').split())
PACKET_KEYS=set(('authority clean contract_hours counts dynamic_fields execution_supported first_hour fixture_identity '
    'formal_result last_hour later_scope limits_are method native_authorized observation_end plan proposed_stop_limits '
    'registration_end required_before_execution resource_admission schedule schedule_sha schema selected_contingencies '
    'state stop_policy').split())
COUNTS=dict(points=319,QP=160,LP=159,actual=41,contract=278,economic_kkt=12,child_lp_kkt=159,primal_point=148,
    static_request_identities=309,dynamic_actual_request_identities=10,successful_path_model_builds=1276,
    successful_path_imports=638,schedule_generation_request_objects=326,validation_request_objects_per_pass=316,
    validation_passes_for_prepare=2,full_preparation_request_objects=958)


def require(value,message):
    if not value:raise ValueError(message)


def read(path):return json.loads(path.read_bytes())


def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def digest(value):return sha256(encoded(value)).hexdigest()


def stamp(path,allow_links=False):
    info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)
        and not getattr(info,'st_file_attributes',0)&0x400 and (allow_links or info.st_nlink==1),'nonordinary file')
    raw=path.read_bytes();return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def verify_rows(rows):
    require(type(rows) is list and len(rows)==319,'slot count differs')
    require(all(type(r) is dict and set(r)==ROW_KEYS for r in rows),'slot schema differs')
    previous=None;offset=0;actual_slots=[]
    for hour in range(-2,8):
        roles=['reference_base_P0']+(['reference_raw_need'] if hour==1 else [])+['recovery_min_meter','recovery_max_meter','actual_P']
        group=rows[offset:offset+len(roles)];root=offset+1
        require([r['role'] for r in group]==roles,'actual role order differs')
        for r in group:
            require(r['hour']==hour and r['section']=='actual' and r['state_after_actual_slot']==previous
                and r['phase_gate']==('declared_genesis' if previous is None else 'accepted_previous_hour'),'actual carry differs')
            require(r['parent_slot']==(None if r['ordinal']==root else root),'actual parent differs')
            expected_refs=list(range(root,r['ordinal'])) if r['role']=='actual_P' else []
            require(r['reference_slots']==expected_refs,'policy reference edges differ')
        previous=group[-1]['ordinal'];actual_slots.append(previous);offset+=len(roles)
    require(actual_slots==[4,8,12,17,21,25,29,33,37,41],'actual accepted slots differ')
    outages=[dict(branches=[i],generators=[],name='branch_'+str(i)) for i in range(37)]
    outages += [dict(branches=[],generators=[i],name='generator_'+str(i)) for i in range(32)]
    for hour in (1,2):
        group=rows[offset:offset+139];root=offset+1
        require(group[0]['role']=='normal_contract_C' and group[0]['parent_slot'] is None,'contract root differs')
        for index,outage in enumerate(outages):
            firm,raw=group[1+2*index:3+2*index]
            require(firm['role']=='fault_firm_F' and raw['role']=='fault_raw_need'
                and encoded(firm['outage'])==encoded(raw['outage'])==encoded(outage)
                and firm['parent_slot']==raw['parent_slot']==root,'contingency pair differs')
        require(all(r['hour']==hour and r['section']=='contract' and r['state_after_actual_slot']==41
            and r['phase_gate']=='actual_finished' and r['reference_slots']==[] for r in group),'contract gate differs')
        offset+=139
    normal=dict(branches=[],generators=[],name='normal')
    for i,r in enumerate(rows,1):
        require(type(r['ordinal']) is int and r['ordinal']==i and r['serial_after']==(i-1 if i>1 else None),'serial edge differs')
        require(type(r['hour']) is int and all(type(v) is int for v in r['reference_slots']),'edge scalar differs')
        objective={'reference_raw_need':'min_curtailment','fault_raw_need':'min_curtailment',
            'recovery_min_meter':'min_meter','recovery_max_meter':'max_meter'}.get(r['role'],'economic')
        kind='child_lp_kkt' if objective!='economic' else 'economic_kkt' if r['parent_slot'] is None else 'primal_point'
        require(r['objective']==objective and r['evidence_kind']==kind,'evidence family differs')
        dynamic=r['role']=='actual_P';parent=r['parent_slot']
        require(r['request_sha'] is None if dynamic else type(r['request_sha']) is str
            and re.fullmatch('[0-9a-f]{64}',r['request_sha']) is not None,'request SHA form differs')
        require(all(r[k] is None for k in ('bound_query_sha','parent_point_sha','parent_economic_sha')),'future numeric SHA filled')
        require(r['dynamic_reason']==('policy_power_and_parent_point' if dynamic else 'bound_parent_point' if parent else None),'dynamic reason differs')
        if parent is None:require(r['parent_request_sha'] is None,'root parent SHA differs')
        else:
            require(type(parent) is int and 0<parent<i and rows[parent-1]['request_sha']==r['parent_request_sha']
                and rows[parent-1]['hour']==r['hour'] and rows[parent-1]['section']==r['section'],'bound parent request differs')
        if r['section']=='actual':
            expected=outages[0] if r['hour']==1 and r['role']!='reference_base_P0' else normal
            require(encoded(r['outage'])==encoded(expected),'actual outage differs')
        elif r['role']=='normal_contract_C':require(encoded(r['outage'])==encoded(normal),'contract normal outage differs')
    require(Counter(r['evidence_kind'] for r in rows)==Counter(economic_kkt=12,child_lp_kkt=159,primal_point=148),'family counts differ')
    require(sum(r['objective']=='economic' for r in rows)==160 and sum(r['request_sha'] is None for r in rows)==10,'QP/dynamic counts differ')


def main():
    files={p.name:stamp(p) for p in PACK.iterdir()}
    require(set(files)=={'packet.json','context.json','observation.json'},'packet file set differs')
    p=read(PACK/'packet.json');context=read(PACK/'context.json');observation=read(PACK/'observation.json')
    require(set(p)==PACKET_KEYS and p['schema']=='staged_rts24_p2_preparation_v1' and p['state']=='PREPARATION_ONLY','packet schema differs')
    require(encoded(p['counts'])==encoded(COUNTS),'count table differs')
    require((p['plan'],p['clean'],p['method'],p['first_hour'],p['registration_end'],p['observation_end'],p['last_hour'])
        ==('on_time','early','full_temporal',-2,4,8,7) and p['contract_hours']==[1,2] and p['selected_contingencies']==69,'scope differs')
    require(p['later_scope']==dict(single_method_full_hourly_contract_requests=1431,three_method_full_hourly_contract_requests=4273,
        DE_inputs_and_selection='OPEN',full_FX_temporal_backing='OPEN'),'later scope differs')
    for obj in (p,context,observation):
        require(obj['authority']=='DRAFT_NONAUTHORITATIVE' and all(obj[k] is False
            for k in ('native_authorized','execution_supported','resource_admission')),'authority differs')
    require(p['formal_result'] is False and context['preparation_only'] is True and observation['preparation_completed'] is True,'metadata terminal differs')
    require(observation['packet_pin']==files['packet.json'] and observation['context_pin']==files['context.json'],'saved byte pins differ')
    require(observation['P1_files_rechecked']==683 and observation['proposed_execution_directory_absent'] is True,'P1 bookend absent')
    require(Path(context['proposed_execution_directory'])==ROOT/'results/tables/staged_rts24_p2_native_v1_non_authoritative/p2_01'
        and not Path(context['proposed_execution_directory']).exists(),'P2 execution directory exists or changed')
    verify_rows(p['schedule'])
    require(p['schedule_sha']==digest(p['schedule'])=='5ac4947ff7d2e750dff8e6afa66c305fdc7a860c2eaac529d5b098bf0b09906b','schedule binding differs')
    sources=context['source_pins'];require(len(sources)==55 and all(stamp(ROOT/n)==v for n,v in sources.items()),'source pin changed')
    for name in ('units_04','execute_01'):
        check=read(CHECKS/(name+'.exit.json'))
        require(check['exit_code']==0 and check['source_pins_unchanged'] is True
            and all(stamp(ROOT/n)==v==sources[n] for n,v in check['source_pins'].items()),'check/source binding differs')
    command=read(CHECKS/'execute_01.exit.json');review=read(CHECKS/'preparation_review_01.json')
    require(command['timed_out'] is False and command['attempt_count']==1 and command['automatic_retry'] is False
        and command['command_wall_seconds']<60 and command['review_pin']==stamp(CHECKS/'preparation_review_01.json'),'command terminal differs')
    require((CHECKS/'execute_01.stderr.log').read_bytes()==b'' and review['source_pins']==sources,'review scope differs')
    runtime=context['preparation_runtime']
    require(len(runtime['application_modules'])==40 and len(runtime['functions'])==74
        and len(runtime['classes'])==20 and len(runtime['stdlib'])==211,'runtime shape differs')
    require(set(runtime['preparation_sources'])==set(sources) and context['metadata_warmup_added_stdlib']==['email.feedparser','email.parser'],'warmup/source inventory differs')
    require(context['loaded_module_names']==sorted(set(context['loaded_module_names']))
        and set(runtime['application_modules'])<=set(context['loaded_module_names']),'loaded inventory differs')
    runtime_files={runtime['executable']:runtime['executable_pin']}
    runtime_files.update({row['resolved']:row['pin'] for row in runtime['stdlib'].values() if 'pin' in row})
    require(all(stamp(Path(n),allow_links=True)==v for n,v in runtime_files.items()),'runtime file bytes changed')
    require(all(stamp(Path(v['path']))==v['pin']==sources[Path(v['path']).relative_to(ROOT).as_posix()]
        for v in runtime['application_modules'].values()),'application source binding differs')
    require(all(stamp(Path(v['path']))['sha256']==v['source_sha'] for v in runtime['functions'].values()),'function source binding differs')
    require(encoded(context['original_runtime_bindings'])==encoded(read(P1/'start.json')['pins']),'original runtime differs')
    require(stamp(PRIOR)==context['P1_postcheck_pin'] and context['P1_postcheck_pin']['sha256']==
        'c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473','original postcheck anchor differs')
    prior=read(PRIOR);require({f.relative_to(P1).as_posix():stamp(f) for f in P1.rglob('*') if f.is_file()}==prior['p1_files'],'P1 bytes changed')
    preserved=read(POST/'prior_preservation_inventory.json')
    require(len(preserved)==196 and all(stamp(ROOT/n)==v for n,v in preserved.items()),'previous published paths changed')
    for name in ('P1_and_prior','saved_profile','shadow_v1','shadow_v2'):
        old=read(POST/(name+'.exit.json'))
        require(old['exit_code']==0 and old['exact_prior_stdout'] is True and (POST/(name+'.stderr.log')).read_bytes()==b'','old postcheck differs')
    require(stamp(POST/'P1_and_prior.stdout.json')==stamp(PRIOR),'P1 postcheck stdout differs')
    related=read(CHECKS/'related_01.exit.json');diagnosis=read(CHECKS/'related_failure_diagnosis_01.stdout.json')
    require(related['exit_code']==1 and related['source_pins_unchanged'] is True and all(diagnosis['matches'].values())
        and diagnosis['psutil_loaded'] is False and diagnosis['P1_output_exists'] is True,'historical test diagnosis differs')
    require(all(stamp(ROOT/n)==v for n,v in related['source_pins'].items()),'related regression source drift')
    require(files=={f.name:stamp(f) for f in PACK.iterdir()},'saved packet changed during check')
    return dict(authority='DRAFT_NONAUTHORITATIVE',script=stamp(Path(__file__)),packet_files=files,
        packet_file_count=3,packet_bytes=sum(v['bytes'] for v in files.values()),schedule_sha=p['schedule_sha'],counts=COUNTS,
        source_files_unchanged=55,application_modules=40,functions=74,stdlib_modules=211,declared_runtime_files_rehashed=len(runtime_files),
        P1_files_unchanged=683,P1_bytes_unchanged=sum(v['bytes'] for v in prior['p1_files'].values()),
        B1_B3_saved_files=prior['B1_B3_saved_files'],prior_checkpoint_paths=prior['unique_prior_checkpoint_paths'],
        previous_published_paths_unchanged=len(preserved),ordinary_targeted_passed=38,related_passed=60,related_failed=1,
        historical_failure_explained=True,command_wall_seconds=command['command_wall_seconds'],new_model_builds=0,new_native_calls=0,new_replays=0,
        native_authorized=False,execution_supported=False,resource_admission=False,formal_result=False,
        C_overall_performance_review_complete=False,scope='saved metadata byte and DAG arithmetic; no numeric execution or scientific replay')


if __name__=='__main__':print(json.dumps(main(),sort_keys=True,indent=2,allow_nan=False))
