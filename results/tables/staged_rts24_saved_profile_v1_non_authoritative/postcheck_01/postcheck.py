"""Read-only terminal/pin arithmetic; no model, solver or journal replay."""
from hashlib import sha256
import json
from pathlib import Path
import stat
import subprocess

ROOT=Path(__file__).resolve().parents[4]
BASE=Path(__file__).resolve().parent.parent
PROFILE=BASE/'profile_01'
P1=ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'
PRIOR=P1.parent/'p1_execution_review_01/postcheck_03.stdout.json'


def require(value,message):
    if not value:raise ValueError(message)


def read(path):return json.loads(path.read_bytes())


def stamp(path):
    info=path.lstat()
    require(stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)
        and not getattr(info,'st_file_attributes',0)&0x400,'nonordinary file')
    raw=path.read_bytes()
    return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def main():
    admission=read(BASE/'development_checks_01/prelaunch_01.json')
    require(all(stamp(ROOT/n)==v for n,v in admission['source_pins'].items()),'diagnostic source changed')
    require(stamp(PRIOR)==admission['saved_postcheck'],'saved postcheck changed')
    prior=read(PRIOR);expected=prior['p1_files']
    require({p.relative_to(P1).as_posix():stamp(p) for p in P1.rglob('*') if p.is_file()}==expected,'P1 bytes changed')
    adopted=read(PROFILE/'postquiet.json');pins=adopted['output_pins']
    require(set(p.name for p in PROFILE.iterdir())==set(pins)|{'postquiet.json','launcher.json'},'profile file set changed')
    require(len(pins)==10 and all(stamp(PROFILE/n)==v for n,v in pins.items()),'profile artifacts changed')
    require(adopted['P1_bytes_rechecked_after_quiet'] is True,'missing postquiet input bookend')
    report=read(PROFILE/'report.json');observed=read(PROFILE/'observations.json')
    require(report['authority']=='DRAFT_NONAUTHORITATIVE' and report['science_metrics_match'] is True
        and report['P1_bytes_unchanged'] is True,'diagnostic outcome differs')
    require(all(report[k] is False for k in ('formal_result','resource_admission','C_overall_performance_review_complete','full_139_executed','fx_temporal_backing')),'claim scope differs')
    require(report['saved_files_checked']==len(expected) and report['saved_bytes_checked']==sum(v['bytes'] for v in expected.values()),'P1 count differs')
    require(report['source_sha']==adopted['source_sha']==admission['source_pins']['experiments/staged_rts24_saved_profile_v1.py']['sha256']
        and report['contract_sha']==adopted['contract_sha']==admission['source_pins']['docs/plan/staged_deliverability_c_saved_profile_contract_v1.md']['sha256']
        and report['saved_input_sha']==adopted['prior_sha']==stamp(PRIOR)['sha256'],'terminal binding differs')
    forbidden={'native_factory_requested','forbidden_factory_requests','explicit_compile','importer_recompile','publication_requested_bytes'}
    forbidden|={prefix+label+'_'+suffix for prefix in ('','replay/') for label in ('native_call','native_model','pyomo_build','numeric_compile','cas_put','publication') for suffix in ('attempts','returned','raised')}
    require(observed['allow_native'] is False and all(observed['counts'].get(k,0)==0 for k in forbidden),'unexpected new evidence or solver')
    require(report['solver_calls']==report['new_models']==0 and observed['counts']['fingerprints_returned']==2
        and observed['counts']['journal_reopen_returned']==1,'diagnostic call count differs')
    launcher=read(PROFILE/'launcher.json');w=launcher['quiescence_witness'];limits=admission['limits']
    require(launcher['exit_code']==0 and launcher['stop_reason'] is None and launcher['monitor_error'] is None
        and launcher['cleanup_error'] is None and launcher['job_quiet_confirmed'] is True,'Job terminal failure')
    require(w['complete_inventory'] is w['all_handles_signaled'] is True and w['active_processes']==0 and w['final_pids']==[]
        and w['total_processes']==w['observed_unique_member_handles']==len(w['member_identities'])
        and len({(p['pid'],p['creation_filetime']) for p in w['member_identities']})==w['total_processes'],'Job ownership not closed')
    require(launcher['outer_seconds']<=limits['wall_seconds'] and launcher['rss_observation_available'] is True
        and launcher['sampled_tree_peak_rss_bytes']<=limits['rss_bytes']
        and launcher['terminal_files']==len(pins) and launcher['terminal_bytes']==sum(v['bytes'] for v in pins.values())
        and launcher['terminal_files']+2<=limits['files'],'diagnostic caps/counts differ')
    command=read(BASE/'development_checks_01/command_01.exit.json');require(command['exit_code']==0,'command failure')
    statistics={}
    for label,field in [('fingerprints','one_profiled_fingerprint_seconds'),('reopen','one_profiled_reopen_seconds')]:
        data=read(PROFILE/(label+'_stats.json'))
        require(data['function_count']>0 and data['profiled_wall_seconds']==report[field]
            and stamp(PROFILE/(label+'.prof'))['bytes']>0,'missing/nonmatching profile')
        for table,key in [('top_self','self_seconds'),('top_cumulative','cumulative_seconds')]:
            values=[r[key] for r in data[table]]
            require(len(values)==min(80,data['function_count']) and values==sorted(values,reverse=True),'profile order differs')
        statistics[label]=dict(wall_seconds=data['profiled_wall_seconds'],function_count=data['function_count'])
    old_source=P1.parent/'p1_execution_review_01/postcheck.py'
    require(stamp(old_source)==dict(bytes=14152,sha256='161b69a7f39ed5981cf755596cf1465438d335b41a1198826fa0f7be06bd3d88'),'old postcheck source changed')
    return dict(authority='DRAFT_NONAUTHORITATIVE',formal_result=False,resource_admission=False,
        script=stamp(Path(__file__)),source_pins=admission['source_pins'],saved_P1_files=len(expected),
        saved_P1_bytes=sum(v['bytes'] for v in expected.values()),P1_bytes_unchanged=True,
        profile_files={p.name:stamp(p) for p in PROFILE.iterdir()},profile_statistics=statistics,
        command_wall_seconds=command['command_wall_seconds'],job_wall_seconds=launcher['outer_seconds'],
        sampled_tree_peak_rss_bytes=launcher['sampled_tree_peak_rss_bytes'],owned_processes=w['total_processes'],
        new_solver_calls=0,new_models=0,new_journal_replays_by_postcheck=0,
        scope='saved_pins_terminal_and_profile_arithmetic_not_scientific_reconstruction_or_speed_comparison')


if __name__=='__main__':print(json.dumps(main(),sort_keys=True,indent=2,allow_nan=False))
