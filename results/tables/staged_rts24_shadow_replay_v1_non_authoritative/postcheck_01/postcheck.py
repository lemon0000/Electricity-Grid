"""Saved failure, provenance and resource arithmetic; no research imports/replay."""
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


def require(value,message):
    if not value:raise ValueError(message)


def read(path):return json.loads(path.read_bytes())


def stamp(path):
    info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)
        and not getattr(info,'st_file_attributes',0)&0x400 and info.st_nlink==1,'nonordinary file')
    raw=path.read_bytes()
    return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def main():
    files={p.name:stamp(p) for p in ATTEMPT.iterdir()}
    require(set(files)=={'start.json','runtime_before.json','events.jsonl','worker.stdout.log',
        'worker.stderr.log','failure.json','adoption_failure.json','launcher.json'},'failure file set differs')
    start=read(ATTEMPT/'start.json');launcher=read(ATTEMPT/'launcher.json')
    require(launcher['argv'][-1]==files['start.json']['sha256'],'start binding differs')
    require(read(ATTEMPT/'runtime_before.json')==start['runtime'],'saved initial runtime differs')
    require(all(stamp(ROOT/n)==v for n,v in start['source_pins'].items()),'attempt source changed')
    units=read(CHECKS/'units_08.exit.json')
    require(units['exit_code']==0 and all(stamp(ROOT/n)==v for n,v in units['source_pins'].items()),'targeted check binding differs')
    require(all(start['source_pins'][n]==v for n,v in units['source_pins'].items()),'attempt/check sources differ')
    failure=read(ATTEMPT/'failure.json');adoption=read(ATTEMPT/'adoption_failure.json')
    require(failure==dict(accepted_success=False,scientific_outcome='unresolved',type='ShadowIncomplete',
        message="shadow comparison incomplete: {'reason': 'strict_unsupported', 'function': 'dumps'}"),'failure differs')
    require(adoption['accepted_success'] is False,'failure incorrectly adopted')
    require(launcher['exit_code']==2 and launcher['stop_reason']=='child_exit_nonzero'
        and launcher['job_quiet_confirmed'] is True and launcher['cleanup_error'] is None
        and launcher['monitor_error'] is None,'process terminal differs')
    witness=launcher['quiescence_witness']
    require(witness['all_handles_signaled'] is True and witness['complete_inventory'] is True
        and witness['active_processes']==0 and witness['final_pids']==[]
        and witness['observed_unique_member_handles']==witness['total_processes']==len(witness['member_identities'])==2,'quiet witness differs')
    require(launcher['outer_seconds']<60 and launcher['sampled_tree_peak_rss_bytes']<=512*1024**2
        and sum(v['bytes'] for v in files.values())<16*1024**2 and len(files)<64,'registered cap exceeded')
    events=[json.loads(line) for line in (ATTEMPT/'events.jsonl').read_bytes().splitlines()]
    progress=[e['completed'] for e in events if e['stage']=='digest_progress']
    require(progress==list(range(128,2433,128)) and events[-1]['stage']=='digest_progress'
        and not any(e['stage']=='complete' for e in events),'progress boundary differs')
    require(files['worker.stdout.log']['bytes']==0 and files['worker.stderr.log']['bytes']>0,'worker log differs')
    prior=read(PRIOR)
    require(stamp(PRIOR)['sha256']=='c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473','P1 anchor changed')
    require({p.relative_to(P1).as_posix():stamp(p) for p in P1.rglob('*') if p.is_file()}==prior['p1_files'],'P1 bytes changed')
    require(stamp(POST/'P1_and_prior.stdout.json')==stamp(PRIOR),'old P1 postcheck differs')
    require(read(POST/'P1_and_prior.exit.json')['exit_code']==0
        and read(POST/'P1_and_prior.exit.json')['exact_prior_stdout'] is True,'P1 postcheck did not finish')
    preserved=read(POST/'prior_preservation_inventory.json')
    require(len(preserved)==68 and all(stamp(ROOT/n)==v for n,v in preserved.items()),'prior profile/plain bytes changed')
    require(read(POST/'saved_profile.exit.json')['exit_code']==0
        and read(POST/'saved_profile.exit.json')['exact_prior_stdout'] is True,'prior profile postcheck did not finish')
    command=read(CHECKS/'execute_01.exit.json')
    require(command['exit_code']==1 and command['attempt_count']==1 and command['automatic_retry'] is False,'command terminal differs')
    require(files=={p.name:stamp(p) for p in ATTEMPT.iterdir()},'failure bytes changed during check')
    return dict(authority='DRAFT_NONAUTHORITATIVE',script=stamp(Path(__file__)),attempt_files=files,
        attempt_file_count=len(files),attempt_bytes=sum(v['bytes'] for v in files.values()),
        command_exit=1,worker_exit=2,command_wall_seconds=command['command_wall_seconds'],
        Job_wall_seconds=launcher['outer_seconds'],sampled_tree_peak_rss_bytes=launcher['sampled_tree_peak_rss_bytes'],
        peak_job_commit_bytes=launcher['peak_job_commit_bytes'],quiet_member_handles=2,
        first_failure='strict_unsupported',full_strict_equivalence_established=False,
        exact_unsupported_count=None,first_unsupported_caller=None,accepted_digest_pairs=None,
        science_metrics_match_by_attempt=None,monitor_cleaned_by_attempt=None,last_saved_progress=progress[-1],
        source_files_unchanged=len(start['source_pins']),P1_files_unchanged=len(prior['p1_files']),
        P1_bytes_unchanged=sum(v['bytes'] for v in prior['p1_files'].values()),
        B1_B3_saved_files=prior['B1_B3_saved_files'],prior_checkpoint_paths=prior['unique_prior_checkpoint_paths'],
        prior_profile_plain_paths_unchanged=len(preserved),new_replay_or_solver_by_postcheck=0,
        formal_result=False,resource_admission=False,C_overall_performance_review_complete=False,
        scope='saved_failure_and_byte_provenance_not_full_scientific_replay_or_candidate_fallback_rejection')


if __name__=='__main__':print(json.dumps(main(),sort_keys=True,indent=2,allow_nan=False))
