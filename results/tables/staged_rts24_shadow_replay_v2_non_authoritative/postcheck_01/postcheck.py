"""Read-only terminal counters and byte bindings; no research imports or replay."""
from hashlib import sha256
import json
from pathlib import Path
import stat

ROOT=Path(__file__).resolve().parents[4]
BASE=Path(__file__).resolve().parent.parent
ATTEMPT=BASE/'shadow_01'
POST=BASE/'postcheck_01'
CHECKS=BASE/'development_checks_01'
P1=ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
PRIOR=P1.parent/'p1_execution_review_01/postcheck_03.stdout.json'
STAGES=dict(reopen=1,replay_entry=6,prepare_hour=10,propose_hour=10,accept_hour=5,
    audit_execution=17,audit_child_lp=118,execution_summary=1)
EXPECTED=dict(digest_started=2547,parent_json_returns=2547,digest_returned=2547,strict_byte_compares=2547,json_returns=4861)
EXPECTED.update({name+'/'+kind:count for name,count in STAGES.items() for kind in ('started','returned')})


def require(value,message):
    if not value:raise ValueError(message)


def read(path):return json.loads(path.read_bytes())


def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def digest(value):return sha256(encoded(value)).hexdigest()


def stamp(path,allow_links=False):
    info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)
        and not getattr(info,'st_file_attributes',0)&0x400 and (allow_links or info.st_nlink==1),'nonordinary file')
    raw=path.read_bytes()
    return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def main():
    files={p.name:stamp(p) for p in ATTEMPT.iterdir()}
    worker_files={'start.json','events.jsonl','worker.stdout.log','worker.stderr.log',
        'runtime_before.json','runtime_after.json','shadow.json','report.json'}
    require(set(files)==worker_files|{'postquiet.json','launcher.json'},'terminal file set differs')
    adopted=read(ATTEMPT/'postquiet.json');start=read(ATTEMPT/'start.json')
    require(set(adopted['output_pins'])==worker_files and all(files[n]==v for n,v in adopted['output_pins'].items()),'postquiet bytes changed')
    require(adopted['P1_rechecked_after_quiet'] is True,'P1 postquiet bookend missing')
    require(len(start['source_pins'])==54 and all(stamp(ROOT/n)==v for n,v in start['source_pins'].items()),'source pin changed')
    require('docs/plan/staged_deliverability_c_shadow_replay_contract_v2.md' in start['source_pins'],'v2 contract not bound')
    for name in ('units_04','plain_01'):
        checks=read(CHECKS/(name+'.exit.json'))
        require(checks['exit_code']==0 and all(stamp(ROOT/n)==v==start['source_pins'][n] for n,v in checks['source_pins'].items()),'ordinary check source differs')
    runtime=start['runtime']
    require(encoded(read(ATTEMPT/'runtime_before.json'))==encoded(runtime)==encoded(read(ATTEMPT/'runtime_after.json'))
        and files['runtime_before.json']==files['runtime_after.json'],'runtime bookends differ')
    require(len(runtime['application_modules'])==38 and len(runtime['functions'])==56
        and len(runtime['classes'])==20 and len(runtime['stdlib'])==211,'runtime closure shape differs')
    require(runtime['successor_domain']=='exact_str_int_dict_keys_20_registered_classes_depth_64_stationary_same_thread','successor domain differs')
    runtime_files={runtime['executable']:runtime['executable_pin']}
    runtime_files.update({row['resolved']:row['pin'] for row in runtime['stdlib'].values() if 'pin' in row})
    require(all(stamp(Path(n),allow_links=True)==v for n,v in runtime_files.items()),'saved runtime file bytes changed')
    require(all(stamp(Path(row['path']))==row['pin']==start['source_pins'][str(Path(row['path']).relative_to(ROOT)).replace('\\','/')]
        for row in runtime['application_modules'].values()),'loaded application paths not bound to sources')
    require(encoded(start['legacy_pins'])==encoded(read(P1/'start.json')['pins']),'legacy runtime differs')
    shadow=read(ATTEMPT/'shadow.json');counts=shadow['counts'];callers=shadow['callers']
    require(encoded(counts)==encoded(EXPECTED) and all(type(v) is int for v in counts.values()),'fixed counts differ')
    require(shadow['authority']=='DRAFT_NONAUTHORITATIVE' and shadow['first_error'] is None
        and type(shadow['pending']) is int and shadow['pending']==0 and shadow['monitor_cleaned'] is True,'shadow incomplete')
    require(all(type(k) is str and type(v) is int and v>0 for k,v in callers.items()) and sum(callers.values())==2547,'caller counts differ')
    child=sum(v for k,v in callers.items() if k.split('|')[1]=='audit_child_lp'
        and Path(k.split('|')[0]).resolve()==ROOT/'src/staged_rts24_child_optimality_v1.py')
    require(child==118 and sum(callers.values())-child==2429,'fixed alias partition differs')
    report=read(ATTEMPT/'report.json');metrics=read(P1/'fresh.json')['metrics']
    require(encoded(report['metrics'])==encoded(metrics),'original scientific metrics differ')
    for key in ('formal_result','resource_admission','C_overall_performance_review_complete','full_139_executed','fx_temporal_backing'):
        require(report[key] is False,'claim flag changed: '+key)
    require(report['equivalent_digest_calls']==2547 and report['direct_alias_calls']==118
        and report['other_digest_calls']==2429 and report['registered_forbidden_calls']==0,'report count differs')
    for key,value in (('source_pins_sha',digest(start['source_pins'])),('runtime_pins_sha',digest(runtime))):
        require(report[key]==adopted[key]==value,'adopted identity differs')
    require(report['legacy_pins_sha']==digest(start['legacy_pins']),'legacy identity digest differs')
    require(files['worker.stdout.log']['bytes']==files['worker.stderr.log']['bytes']==0,'worker output unexpected')
    events=[json.loads(line) for line in (ATTEMPT/'events.jsonl').read_bytes().splitlines()]
    require(events==[dict(stage='inputs_checked'),dict(stage='reopen_started')]
        +[dict(stage='digest_progress',completed=n) for n in range(128,2433,128)]+[dict(stage='complete')],'progress trace differs')
    launcher=read(ATTEMPT/'launcher.json');w=launcher['quiescence_witness']
    require(launcher['exit_code']==0 and launcher['stop_reason'] is None and launcher['job_quiet_confirmed'] is True
        and launcher['monitor_error'] is None and launcher['cleanup_error'] is None,'process terminal differs')
    require(launcher['argv'][-1]==files['start.json']['sha256'],'start SHA not bound to worker')
    require(w['all_handles_signaled'] is True and w['complete_inventory'] is True and w['active_processes']==0
        and w['final_pids']==[] and w['observed_unique_member_handles']==w['total_processes']==len(w['member_identities'])==2,'quiet witness differs')
    require(launcher['outer_seconds']<60 and launcher['sampled_tree_peak_rss_bytes']<=512*1024**2
        and sum(v['bytes'] for v in files.values())<16*1024**2 and len(files)<64,'budget cap exceeded')
    require(stamp(PRIOR)['sha256']=='c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473','P1 anchor changed')
    prior=read(PRIOR)
    require({p.relative_to(P1).as_posix():stamp(p) for p in P1.rglob('*') if p.is_file()}==prior['p1_files'],'P1 bytes changed')
    preserved=read(POST/'prior_preservation_inventory.json')
    require(len(preserved)==135 and all(stamp(ROOT/n)==v for n,v in preserved.items()),'previous published bytes changed')
    for name in ('P1_and_prior','saved_profile','shadow_v1'):
        record=read(POST/(name+'.exit.json'))
        require(record['exit_code']==0 and record['exact_prior_stdout'] is True and (POST/(name+'.stderr.log')).read_bytes()==b'','old postcheck not reproduced')
    require(stamp(POST/'P1_and_prior.stdout.json')==stamp(PRIOR),'P1 postcheck bytes differ')
    command=read(CHECKS/'execute_01.exit.json')
    require(command['exit_code']==0 and command['attempt_count']==1 and command['automatic_retry'] is False,'command did not finish once')
    require(files=={p.name:stamp(p) for p in ATTEMPT.iterdir()},'terminal bytes changed during check')
    return dict(authority='DRAFT_NONAUTHORITATIVE',script=stamp(Path(__file__)),attempt_files=files,
        attempt_file_count=len(files),attempt_bytes=sum(v['bytes'] for v in files.values()),
        equivalent_digest_pairs=2547,child_alias_pairs=118,other_pairs=2429,json_returns=4861,stage_counts=STAGES,
        scientific_metrics_match=True,scientific_outcome=metrics['scientific_outcome'],coverage_complete=metrics['summary']['coverage_complete'],
        method_conditions_satisfied=metrics['summary']['method_conditions_satisfied'],full_replay_conditions_satisfied=metrics['summary']['full_replay_conditions_satisfied'],
        command_wall_seconds=command['command_wall_seconds'],Job_wall_seconds=launcher['outer_seconds'],
        sampled_tree_peak_rss_bytes=launcher['sampled_tree_peak_rss_bytes'],peak_job_commit_bytes=launcher['peak_job_commit_bytes'],
        quiet_member_handles=2,source_files_unchanged=54,declared_runtime_files_rehashed=len(runtime_files),
        P1_files_unchanged=len(prior['p1_files']),P1_bytes_unchanged=sum(v['bytes'] for v in prior['p1_files'].values()),
        B1_B3_saved_files=prior['B1_B3_saved_files'],prior_checkpoint_paths=prior['unique_prior_checkpoint_paths'],
        previous_published_paths_unchanged=len(preserved),new_replay_or_solver_by_postcheck=0,
        formal_result=False,resource_admission=False,C_overall_performance_review_complete=False,
        scope='saved_terminal_counts_byte_identity_and_resource_arithmetic_not_new_scientific_replay_or_speedup')


if __name__=='__main__':print(json.dumps(main(),sort_keys=True,indent=2,allow_nan=False))
