"""One supervised fixed-size origin packet diagnostic, without retry."""
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


def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_bytes())
def save(path,value):
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')


def main():
    started=time.monotonic()
    if sys.flags.optimize!=0:raise RuntimeError('diagnostic requires enabled Python assertions')
    label=sys.argv[1]
    if not label.replace('_','').isalnum():raise ValueError('fresh diagnostic label required')
    out=HERE/label;out.mkdir()
    plan_path=HERE/'plan_v4.json';plan=load(plan_path)
    pins=plan['bindings']|{str(plan_path):pin(plan_path)}
    command=[sys.executable,'-u','-B',str(HERE/'packet_worker_v2.py'),str(out)]
    save(out/'request.json',dict(command=command,sources_sha256=pins,formal_result=False))
    owned={};process=None;reason=None;worker=None;error=None;cleanup=[]
    sources_checked_before=0;sources_checked_after=0;changed=[]
    peak_rss=peak_disk=0;stamp=0;last_activity=started;next_heartbeat=0
    console=os.path.normcase(str(Path(os.environ['SystemRoot'])/'System32/conhost.exe'))
    def live():
        found=[]
        for pid,created in tuple(owned.items()):
            try:
                item=psutil.Process(pid)
                if item.create_time()==created and item.is_running():found.append(item)
            except psutil.NoSuchProcess:pass
        return found
    try:
        for path,value in pins.items():
            if time.monotonic()-started>plan['wall_limit_seconds']:
                reason='whole_wall_limit_before_spawn';raise TimeoutError(reason)
            if pin(path)!=value:raise ValueError('registered source changed: '+path)
            sources_checked_before+=1
        tested=out/'tested_bytes';tested.mkdir()
        for name in ('packet_worker_v2.py','run_packet_v2.py','plan_v4.json','design_and_budget.md'):
            (tested/name).write_bytes((HERE/name).read_bytes())
        if time.monotonic()-started>plan['wall_limit_seconds']:
            reason='whole_wall_limit_before_spawn';raise TimeoutError(reason)
        last_activity=time.monotonic()
        with (out/'stdout.txt').open('wb') as stdout,(out/'stderr.txt').open('wb') as stderr:
            process=subprocess.Popen(command,cwd=REPO,stdout=stdout,stderr=stderr,
                env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),
                creationflags=subprocess.CREATE_NO_WINDOW)
            owned[process.pid]=psutil.Process(process.pid).create_time()
            while True:
                for item in live():
                    for child in item.children(recursive=True):owned[child.pid]=child.create_time()
                supervisor_rss=psutil.Process(os.getpid()).memory_info().rss
                rss=supervisor_rss;unexpected=[]
                for item in live():
                    try:
                        rss+=item.memory_info().rss
                        if item.pid!=process.pid and (os.path.normcase(item.exe())!=console or item.ppid()!=process.pid):
                            unexpected.append(item.pid)
                    except psutil.NoSuchProcess:pass
                now=time.monotonic();disk=sum(path.stat().st_size for path in out.rglob('*') if path.is_file())
                activity=out/'activity.json';current=activity.stat().st_mtime_ns if activity.exists() else 0
                if current!=stamp:stamp,last_activity=current,now
                row=dict(elapsed_seconds=now-started,no_activity_seconds=now-last_activity,
                    supervisor_rss_bytes=supervisor_rss,worker_tree_rss_bytes=rss-supervisor_rss,
                    rss_bytes=rss,output_logical_bytes=disk)
                peak_rss=max(peak_rss,rss);peak_disk=max(peak_disk,disk)
                with (out/'monitor.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(row)+'\n')
                if now>=next_heartbeat:print(json.dumps(row),flush=True);next_heartbeat=now+30
                reason=('wall_limit' if now-started>plan['wall_limit_seconds'] else
                    'no_activity_limit' if now-last_activity>plan['no_activity_limit_seconds'] else
                    'rss_limit' if rss>plan['sampled_owned_RSS_limit_bytes'] else
                    'output_limit' if disk>plan['output_logical_limit_bytes'] else
                    'unexpected_child' if unexpected else None)
                if reason or process.poll() is not None:break
                time.sleep(plan['sample_seconds'])
            if reason:
                for item in reversed(live()):item.kill();cleanup.append(dict(pid=item.pid,reason=reason))
            process.wait(timeout=10)
            if (out/'worker_terminal.json').exists():worker=load(out/'worker_terminal.json')
    except BaseException as caught:error=repr(caught)[:2048]
    finally:
        for item in reversed(live()):
            try:item.kill();cleanup.append(dict(pid=item.pid,reason='owned_tail'))
            except psutil.NoSuchProcess:pass
        psutil.wait_procs(live(),timeout=5)
    remaining=[item.pid for item in live()]
    for name,value in pins.items():
        if time.monotonic()-started>plan['wall_limit_seconds']:
            reason=reason or 'whole_wall_limit_during_postcheck';break
        try:
            if pin(name)!=value:changed.append(name)
            sources_checked_after+=1
        except BaseException as caught:
            error=error or repr(caught)[:2048];break
    if time.monotonic()-started>plan['wall_limit_seconds']:
        reason=reason or 'whole_wall_limit_after_postcheck'
    accepted=(process is not None and process.returncode==0 and reason is None and error is None and not remaining
        and sources_checked_before==sources_checked_after==len(pins)
        and not changed and type(worker) is dict and worker.get('exit_code')==0
        and worker.get('stage_count')==232 and worker.get('relative_hour')==0
        and worker.get('source_correspondence_rechecked') is True
        and worker.get('solver_deny_hooks_restored') is True
        and worker.get('audit_errors')==[] and worker.get('opened_input_pins_changed')==[]
        and type(worker.get('v3_packet_accounting_bytes_at_remember')) is int and worker['v3_packet_accounting_bytes_at_remember']>0
        and type(worker.get('all_packets_container_recursive_bytes')) is int
        and worker['all_packets_container_recursive_bytes']>0
        and set(worker.get('retained_accounting_checkpoints',{}))=={'before_all_packet_validation',
            'after_all_packet_validation','after_field_walks','after_source_revalidation'}
        and all(worker.get(name) is False for name in ('products_are_H192_upper_bounds',
            'products_are_predictions_or_lower_bounds','other_hours_proved_no_larger_than_origin',
            'selected_frame_or_ChildInspection_created','complete_H192_retention_or_all_source_rows_covered'))
        and all(worker.get(name)==0 for name in ('model_builds','Reader_invocations','new_normal_jobs','selector_calls','real_native_solver_calls')))
    terminal=dict(status='DRAFT_NONAUTHORITATIVE',exit_code=0 if accepted else 1,accepted=accepted,
        process_exit_code=None if process is None else process.returncode,reason=reason,error=error,
        outer_seconds=time.monotonic()-started,peak_sampled_tree_rss_bytes=peak_rss,
        peak_output_logical_bytes=peak_disk,observed_processes=owned,observed_processes_remaining=remaining,
        cleanup_events=cleanup,worker=worker,source_pins=len(pins),changed_sources=changed,
        sources_checked_before=sources_checked_before,sources_checked_after=sources_checked_after,
        sampled_RSS_includes_supervisor=True,Python_optimize=sys.flags.optimize,
        source_successor_adopted=False,resource_admission=False,formal_execution_ready=False,formal_result=False)
    save(out/'terminal.json',terminal)
    print(json.dumps({name:terminal[name] for name in ('exit_code','outer_seconds','reason',
        'peak_sampled_tree_rss_bytes','source_pins','changed_sources')}),flush=True)
    return terminal['exit_code']


if __name__=='__main__':raise SystemExit(main())
