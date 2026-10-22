"""Supervise the exact finite failure suite; stop on its first unaccepted case."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def accepted_worker(worker,case):
    if (type(worker) is not dict or type(worker.get('exit_code')) is not int or worker['exit_code']!=0
            or worker.get('case')!=case['case']
            or worker.get('observed_replay_call_counts')!=case['expected_runtime_counts']
            or worker.get('namespace_observations_reached')!=case['namespace_round_expected']
            or any(worker.get(name) is not True for name in ('prior_trace_and_profile_restored',
                'guard_usable_after_fault_restored','saved_case_sha256_equal','injection_reached'))
            or type(worker.get('injection_count')) is not int or worker['injection_count']!=1
            or worker.get('instrumentation_errors')!=[] or worker.get('cleanup_errors')!=[]
            or type(worker.get('activity')) is not dict or worker['activity'].get('rejected_mutations')!=0):
        return False
    if case['case']=='final_read_sharing_error' and any(worker.get(name) is not True for name in (
            'read_only_sharing_handle_closed','sharing_target_identity_before_after_equal')):
        return False
    return True


plan_path=HERE/'plan_v2.json'
plan=json.loads(plan_path.read_bytes())
label=sys.argv[1]
if not label.replace('_','').isalnum():raise ValueError('fresh suite label required')
out=HERE/label;out.mkdir()
pins=plan['inherited_bindings']|plan['source_sha256']|{str(plan_path):sha256(plan_path.read_bytes()).hexdigest()}
changed=[name for name,pin in pins.items() if sha256(Path(name).read_bytes()).hexdigest()!=pin]
if changed:raise ValueError('registered source bytes changed: '+repr(changed))
for path in (HERE/'fault_worker_v1.py',Path(__file__),HERE/'design_and_budget.md',plan_path):
    target=out/'tested_bytes'/path.name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes())


def save(path,value):
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')


def logical_bytes(root):return sum(path.stat().st_size for path in root.rglob('*') if path.is_file())


started=time.monotonic();rows=[];suite_error=None;observed={};peak_rss=peak_disk=0
console=os.path.normcase(str(Path(os.environ['SystemRoot'])/'System32/conhost.exe'))
save(out/'request.json',dict(status='DRAFT_NONAUTHORITATIVE',plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),
    registered_cases=[row['case'] for row in plan['cases']],sources_sha256=pins,
    no_new_normal_jobs=True,real_native_solver_authorized=False,formal_result=False))
try:
    for index,case in enumerate(plan['cases'],1):
        if time.monotonic()-started>=plan['whole_suite_wall_limit_seconds']:
            suite_error='suite wall exhausted before next case launch'
            break
        directory=out/f"{index:02d}_{case['case']}";directory.mkdir()
        tested=directory/'tested_bytes';tested.mkdir()
        (tested/'fault_worker_v1.py').write_bytes((HERE/'fault_worker_v1.py').read_bytes())
        owned={};process=None;reason=None;result={};cleanup=[];case_peak_rss=case_peak_disk=0
        began=time.monotonic();last_activity=began;stamp=0;next_heartbeat=0
        command=[sys.executable,'-u','-B',str(HERE/'fault_worker_v1.py'),case['case'],str(directory)]
        save(directory/'request.json',dict(command=command,case=case,plan_sha256=sha256(plan_path.read_bytes()).hexdigest()))
        def live():
            found=[]
            for pid,created in tuple(owned.items()):
                try:
                    item=psutil.Process(pid)
                    if item.create_time()==created and item.is_running():found.append(item)
                except psutil.NoSuchProcess:pass
            return found
        try:
            with (directory/'stdout.txt').open('wb') as stdout,(directory/'stderr.txt').open('wb') as stderr:
                process=subprocess.Popen(command,cwd=REPO,stdout=stdout,stderr=stderr,
                    env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                owned[process.pid]=psutil.Process(process.pid).create_time()
                while True:
                    for item in live():
                        for child in item.children(recursive=True):owned[child.pid]=child.create_time()
                    rss=0;unexpected=[]
                    for item in live():
                        try:
                            rss+=item.memory_info().rss
                            exe,parent=item.exe(),item.ppid()
                            observed[str(item.pid)]=dict(executable=exe,parent_pid=parent,
                                create_time=item.create_time(),command=item.cmdline())
                            if item.pid!=process.pid and (os.path.normcase(exe)!=console or parent!=process.pid):unexpected.append(item.pid)
                        except psutil.NoSuchProcess:pass
                    now=time.monotonic();disk=logical_bytes(out)
                    activity=directory/'source_read_activity.json'
                    current=activity.stat().st_mtime_ns if activity.exists() else 0
                    if current!=stamp:stamp,last_activity=current,now
                    row=dict(case=case['case'],case_seconds=now-began,suite_seconds=now-started,
                        no_case_read_activity_seconds=now-last_activity,rss_bytes=rss,output_logical_bytes=disk)
                    case_peak_rss=max(case_peak_rss,rss);case_peak_disk=max(case_peak_disk,disk)
                    with (directory/'monitor.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(row)+'\n')
                    if now>=next_heartbeat:print(json.dumps(row),flush=True);next_heartbeat=now+30
                    reason=('suite_wall_limit' if now-started>plan['whole_suite_wall_limit_seconds'] else
                        'case_wall_limit' if now-began>plan['per_case_wall_limit_seconds'] else
                        'no_case_read_activity_limit' if now-last_activity>plan['no_case_read_activity_limit_seconds'] else
                        'rss_limit' if rss>plan['owned_tree_sampled_rss_limit_bytes'] else
                        'output_storage_limit' if disk>plan['output_logical_limit_bytes'] else
                        'unexpected_child' if unexpected else None)
                    if reason or process.poll() is not None:break
                    time.sleep(plan['sample_seconds'])
                if reason:
                    for item in reversed(live()):item.kill();cleanup.append(dict(pid=item.pid,reason=reason))
                process.wait(timeout=10)
                result['exit_code']=process.returncode
                worker=json.loads((directory/'worker_terminal.json').read_bytes())
                result['worker']=worker
                result['worker_accepted']=accepted_worker(worker,case)
        except BaseException as error:result['error']=repr(error)[:2048]
        finally:
            for item in reversed(live()):
                try:item.kill();cleanup.append(dict(pid=item.pid,reason='owned_tail'))
                except psutil.NoSuchProcess:pass
            psutil.wait_procs(live(),timeout=5)
            result.update(case=case['case'],reason=reason,case_outer_seconds=time.monotonic()-began,
                peak_sampled_tree_rss_bytes=case_peak_rss,peak_output_logical_bytes=case_peak_disk,
                observed_processes=owned,observed_processes_remaining=[item.pid for item in live()],cleanup_events=cleanup)
            result['accepted']=(result.get('exit_code')==0 and result.get('worker_accepted') is True
                and reason is None and not result.get('error') and not result['observed_processes_remaining'])
            save(directory/'terminal.json',result)
        rows.append(dict(case=case['case'],terminal=str(directory/'terminal.json'),accepted=result['accepted'],
            case_outer_seconds=result['case_outer_seconds']))
        peak_rss=max(peak_rss,case_peak_rss);peak_disk=max(peak_disk,case_peak_disk)
        print(json.dumps(rows[-1]),flush=True)
        if not result['accepted']:break
except BaseException as error:suite_error=repr(error)[:2048]
finally:
    changed=[name for name,pin in pins.items() if sha256(Path(name).read_bytes()).hexdigest()!=pin]
    accepted=len(rows)==len(plan['cases']) and all(row['accepted'] for row in rows) and not suite_error and not changed
    terminal=dict(status='DRAFT_NONAUTHORITATIVE',exit_code=0 if accepted else 1,cases=rows,
        registered_case_count=len(plan['cases']),completed_case_count=len(rows),error=suite_error,
        outer_seconds=time.monotonic()-started,peak_sampled_tree_rss_bytes=peak_rss,
        peak_output_logical_bytes=peak_disk,observed_images=observed,changed_sources=changed,source_pins=len(pins),
        complete_unobserved_process_tree_proof=False,source_successor_adopted=False,
        resource_admission=False,formal_execution_ready=False,full_192_hour_execution_verified=False,
        non_solver_Win32_API_case='final_read_sharing_error',
        new_normal_jobs=0,real_native_solver_calls=0,real_native_calls=0,
        real_native_calls_scope='solver/native scientific adapter only',formal_result=False)
    save(out/'terminal.json',terminal)
    print(json.dumps({key:terminal[key] for key in ('exit_code','completed_case_count','outer_seconds','changed_sources','peak_sampled_tree_rss_bytes')}),flush=True)
sys.exit(terminal['exit_code'])
