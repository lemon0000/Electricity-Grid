"""Read-only saved-P1 byte, binding and transport arithmetic observation.

No research implementation imports, solver, model construction or replay.
This is not an independent reconstruction of the original scientific model.
"""
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent
P1 = BASE.parent/'p1_01'
REG_SHA = '23577e5d79d3284a260decbfe2258a3103252617953452565a9feeffafbd94e2'


def require(value, message):
    if not value: raise ValueError(message)


def read(path):
    return json.loads(path.read_bytes())


def stamp(path):
    raw=path.read_bytes()
    return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def digest(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def inventory(root):
    paths=list(root.rglob('*'))
    require(all(not p.is_symlink() for p in paths),'symlink in P1')
    return {p.relative_to(root).as_posix():stamp(p) for p in paths if p.is_file()}


def quiet(record):
    w=record['quiescence_witness']
    require(record['exit_code']==0 and record['stop_reason'] is None and record['job_quiet_confirmed'], 'process not successful/quiet')
    require(record['cleanup_error'] is record['monitor_error'] is None,'process cleanup/monitor error')
    ids={(p['pid'],p['creation_filetime']) for p in w['member_identities']}
    require(w['complete_inventory'] and w['all_handles_signaled'] and w['active_processes']==0
        and w['final_pids']==[] and len(ids)==w['observed_unique_member_handles']==w['total_processes'],'process witness incomplete')
    return ids


def cas_check(root):
    paths=list(root.iterdir())
    require(all(p.is_file() and p.suffix=='.json' and sha256(p.read_bytes()).hexdigest()==p.stem for p in paths),'CAS byte/key mismatch')
    def refs(value):
        if isinstance(value,list):
            if len(value)==2 and value[0]=='ref':
                require((root/(value[1]+'.json')).is_file(),'CAS reference missing')
            else:
                for item in value: refs(item)
        elif isinstance(value,dict):
            for item in value.values(): refs(item)
    for p in paths: refs(read(p))
    return len(paths)


def main():
    before=inventory(P1)
    reg_path=BASE.parent/'registration_v1.json';reg=read(reg_path)
    require(stamp(reg_path)['sha256']==REG_SHA,'registration changed')
    start,report,fresh,launcher=map(lambda n:read(P1/n),('start.json','report.json','fresh.json','launcher.json'))
    require(start['pins']==reg['pins'] and start['preserved']==reg['preserved'],'registered input/preservation differs')
    require(digest(read(P1/'request_schedule.json'))==reg['schedule_sha'],'schedule changed')
    for name,pin in reg['pins']['sources'].items(): require(stamp(ROOT/name)==pin,'registered source changed: '+name)
    rt=reg['pins']['runtime']
    for name,h in rt['sources'].items(): require(stamp(ROOT/name)['sha256']==h,'runtime source changed: '+name)
    for pin in rt['external'].values(): require(stamp(Path(pin['path']))['sha256']==pin['sha256'],'selected runtime file changed')
    require(stamp(Path(rt['executable']))['sha256']==rt['executable_sha256'],'interpreter changed')
    completion=read(P1/'completion.json')
    require(all(before[n]==v for n,v in completion['files'].items()),'completion byte drift')
    require(len(completion['files'])==completion['manifest_files']==677,'completion file count')
    require(sum(v['bytes'] for v in completion['files'].values())==completion['logical_bytes'],'completion byte count')
    require(report['package_complete'] and report['failure'] is None and report['formal_result'] is False,'P1 package incomplete')
    require([report[k] for k in ('point_attempts_reserved','native_run_invoked_observed','native_run_returned_observed','points_imported')]==[31]*4,'point totals differ')
    require(report['full_139_executed'] is report['fx_temporal_backing'] is report['resource_admission'] is report['overall_performance_review_complete'] is False,'scope escalation')
    require(fresh['metrics']==report['metrics'] and fresh['solver_calls']==0,'fresh differs')
    outer_ids=quiet(launcher);quiet(read(P1/'fresh_process.json'))
    require(launcher['outer_seconds']<=reg['limits']['wall_seconds'],'outer cap exceeded')
    require(launcher['sampled_tree_peak_rss_bytes']<=reg['limits']['rss_bytes'],'RSS cap exceeded')
    require(sum(v['bytes'] for v in before.values())<=reg['limits']['output_bytes'] and len(before)<=reg['limits']['files'],'final storage cap exceeded')
    counts=Counter();seconds=Counter();point_rows=[];maxima=Counter();point_cas=0;solvers=Counter()
    schedule=read(P1/'request_schedule.json')
    for ordinal in range(1,32):
        directory=P1/'points'/f'point_{ordinal:04d}'
        request,raw,result,process,obs=map(lambda n:read(directory/n),('request.json','native.json','result.json','process.json','point_observations.json'))
        require(quiet(process)<=outer_ids,'point process outside outer inventory')
        require(process['outer_seconds']<=reg['point_limits']['wall_seconds'],'point cap exceeded')
        require(request['ordinal']==ordinal and request['role']==schedule[ordinal-1]['role'] and request['hour']==schedule[ordinal-1]['hour'],'point order differs')
        require(request['registration_sha']==REG_SHA and request['pins_sha']==digest(reg['pins']),'request binding differs')
        require(result['request_sha']==stamp(directory/'request.json')['sha256'] and result['raw_pin']==stamp(directory/'native.json'),'request/raw pin differs')
        require(result['query_sha']==request['query_sha']==raw['problem']['query_sha'],'query differs')
        require(result['problem_sha']==request['problem_sha']==raw['problem_sha']==digest(raw['problem']),'problem differs')
        require(result['status']=='imported' and result['error'] is None and result['infeasibility_inferred'] is False,'point not imported')
        require(raw['run_invoked'] is raw['run_returned'] is True and raw['model_status']=='kOptimal'
            and raw['cleanup_error'] is None and raw['cleanup_status']['name']=='kOk','native status/cleanup differs')
        require(all(a['status']=='kOk' for a in raw['api_calls']),'native API not kOk')
        require(raw['log_pin']==stamp(directory/'native.log'),'native log changed')
        require(all(raw['options'][k]==v for k,v in reg['pins']['options'].items()),'native options differ')
        problem,solution=raw['problem'],raw['solution'];x=solution['col_value']
        require(solution['primal_valid'] and solution['dual_valid'],'native solution invalid')
        require(len(x)==len(problem['columns'])==len(problem['linear'])==len(problem['lower'])==len(problem['upper']),'column dimensions')
        require(len(solution['row_value'])==len(solution['row_dual'])==len(problem['rows']) and len(solution['col_dual'])==len(x),'array dimensions')
        require(all(isfinite(v) for a in ('col_value','row_value','col_dual','row_dual') for v in solution[a]),'nonfinite numeric array')
        gradient=list(problem['linear']);objective=problem['constant']+sum(a*v for a,v in zip(problem['linear'],x))
        for i,j,a in problem['quadratic']:
            objective+=a*x[i]*x[j];gradient[i]+=a*x[j];gradient[j]+=a*x[i]
        obj_echo=abs(objective-raw['objective_value']);row_echo=bound_error=0.
        for i,row in enumerate(problem['rows']):
            activity=sum(a*x[j] for j,a in row['terms']);row_echo=max(row_echo,abs(activity-solution['row_value'][i]))
            for j,a in row['terms']:gradient[j]-=a*solution['row_dual'][i]
            if row['lower'] is not None:bound_error=max(bound_error,row['lower']-activity)
            if row['upper'] is not None:bound_error=max(bound_error,activity-row['upper'])
        for v,lo,hi in zip(x,problem['lower'],problem['upper']):
            if lo is not None:bound_error=max(bound_error,lo-v)
            if hi is not None:bound_error=max(bound_error,v-hi)
        rc_echo=max(abs(a-b) for a,b in zip(gradient,solution['col_dual']))
        require(max(obj_echo,row_echo,rc_echo,bound_error)<=1e-6,'transport arithmetic differs')
        for k,v in dict(objective_echo=obj_echo,row_echo=row_echo,reduced_cost_echo=rc_echo,transport_primal_bounds=bound_error).items():maxima[k]=max(maxima[k],v)
        require(obs['allow_native'] and obs['counts']['native_factory_requested']==obs['counts']['native_call_returned']==1,'native observation differs')
        counts.update(obs['counts']);seconds.update(obs['inclusive_seconds']);solvers[raw['options']['solver']]+=1
        point_cas+=cas_check(directory/'cas'/'objects')
        for ref in ('query_ref',):require((directory/'cas'/'objects'/(request[ref]+'.json')).is_file(),'missing query CAS')
        require((directory/'cas'/'objects'/(result['evidence_ref']+'.json')).is_file(),'missing evidence CAS')
        point_rows.append(dict(ordinal=ordinal,hour=request['hour'],role=request['role'],
            point_outer_seconds=process['outer_seconds'],native_run_seconds=raw['native_run_seconds'],
            native_elapsed_seconds=raw['elapsed_seconds'],raw_pin=result['raw_pin']))
    worker,fo=read(P1/'worker_observations.json'),read(P1/'fresh_observations.json')
    for obs in (worker,fo):
        require(obs['allow_native'] is False,'native allowed in nonpoint process')
        require(all(obs['counts'].get(k,0)==0 for k in ('native_factory_requested','native_call_attempts','native_model_attempts')),'native in replay/worker')
        require(all(obs['counts'].get('replay/'+k+'_attempts',0)==0 for k in ('numeric_compile','pyomo_build','native_call','native_model','cas_put','publication')),'new evidence during replay')
        counts.update(obs['counts']);seconds.update(obs['inclusive_seconds'])
    require(counts['pyomo_build_returned']==124 and counts['numeric_import_returned']==62 and counts['native_call_returned']==31,'model/import counts differ')
    require(solvers==dict(qpasm=16,simplex=15),'QP/LP split differs')
    journal=P1/'journal';journal_cas=cas_check(journal/'objects');gen=read(journal/'genesis.json');previous=stamp(journal/'genesis.json')['sha256'];state=gen['after_state_sha']
    for i in range(1,7):
        p=journal/f'entry_{i:06d}.json';e=read(p)
        require(e['ordinal']==i and e['previous_sha']==previous and e['before_state_sha']==state,'journal chain differs')
        require(set(e['after_cas_keys'])<={p.name for p in (journal/'objects').iterdir()},'retained keys missing')
        previous=stamp(p)['sha256'];state=e['after_state_sha']
    trusted=read(P1/'trusted_binding.json')
    require(previous==trusted['known_head_sha']==report['metrics']['head_sha'] and state==trusted['known_state_sha']==report['metrics']['state_sha'],'trusted head/state differs')
    require(sorted(trusted['known_cas_keys'])==sorted(p.name for p in (journal/'objects').iterdir()),'final CAS set differs')
    summary=report['metrics']['summary']
    require(report['metrics']['scientific_outcome']=='missing_input' and summary['accepted_through']==2 and summary['actual_accepted_hours']==5,'prefix outcome differs')
    require(summary['coverage_complete'] is False and summary['method_conditions_satisfied'] is summary['full_replay_conditions_satisfied'] is None,'coverage/verdict differs')
    prior=read(ROOT/'results/tables/staged_deliverability_c_v1_non_authoritative/saved_audit_01/audit.json')
    require(all(stamp(ROOT/n)==v for f in ('saved_files','repository_pins') for n,v in prior[f].items()),'B1-B3 source/artifact changed')
    old_paths=set()
    for name,sub,fields in (
        ('staged_rts24_append_cost_v1_non_authoritative','execution_observations_01',('source_pins','all_direct_pins','result_files')),
        ('staged_rts24_business_necessary_v1_non_authoritative','',('source_pins','input_pins','artifacts')),
        ('staged_deliverability_evaluation_records_v1_non_authoritative','',('source_pins','input_pins','artifacts'))):
        b=ROOT/'results/tables'/name;checkpoint=b/sub/'checkpoint.json'
        original=subprocess.check_output(['git','show','b5606a920c34d220273737c656daa21cc85737d2:'+checkpoint.relative_to(ROOT).as_posix()],cwd=ROOT)
        require(checkpoint.read_bytes()==original,'historical checkpoint bytes changed')
        c=read(checkpoint)
        for field in fields:
            for n,v in c.get(field,{}).items():
                p=(b if field in ('artifacts','result_files') else ROOT)/n
                require(stamp(p)==v,'prior checkpoint changed: '+str(p));old_paths.add(str(p))
    require(inventory(P1)==before,'P1 bytes changed during postcheck')
    return dict(authority='DRAFT_NONAUTHORITATIVE',formal_result=False,resource_admission=False,
        official_verdict=None,seal=None,receipt=None,scope='saved_P1_bytes_binding_and_transport_echo_not_scientific_model_reconstruction',
        p1_files=before,final_file_count=len(before),final_bytes=sum(v['bytes'] for v in before.values()),
        worker_completion_files=completion['manifest_files'],worker_completion_bytes=completion['logical_bytes'],
        point_CAS_objects=point_cas,journal_CAS_objects=journal_cas,solver_split=dict(solvers),
        selected_observed_counts=dict(counts),selected_inclusive_seconds=dict(seconds),
        transport_arithmetic_maxima=dict(maxima),point_rows=point_rows,
        native_run_seconds_sum=sum(p['native_run_seconds'] for p in point_rows),
        max_point_outer_seconds=max(p['point_outer_seconds'] for p in point_rows),
        fresh_outer_seconds=read(P1/'fresh_process.json')['outer_seconds'],launcher=launcher,
        command_return=read(BASE/'command_return.json'),fresh_metrics_equal=True,read_only_replay_new_evidence_counts_zero=True,
        B1_B3_saved_files=len(prior['saved_files']),unique_prior_checkpoint_paths=len(old_paths),
        after_bytes_equal=True,new_solver_calls_by_postcheck=0)


if __name__=='__main__':
    print(json.dumps(main(),sort_keys=True,separators=(',',':'),allow_nan=False))
