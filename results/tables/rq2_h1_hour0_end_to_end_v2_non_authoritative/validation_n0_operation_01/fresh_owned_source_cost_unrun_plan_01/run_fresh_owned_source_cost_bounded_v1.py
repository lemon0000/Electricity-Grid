"""One fixed cold N0 diagnostic with observed process identity and final cleanup."""
from hashlib import sha256
import json
import msvcrt
from pathlib import Path
import subprocess
import sys
import time
import traceback

import psutil

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
expected_plan_pin,=sys.argv[1:]
plan_name='fresh_owned_source_cost_plan_01.json'
plan_raw=(HERE/plan_name).read_bytes()
if sha256(plan_raw).hexdigest()!=expected_plan_pin:raise ValueError('externally pinned source-cost plan differs')
plan=json.loads(plan_raw)
expected_base='D:/h1_fresh_owned_source_cost_01_non_authoritative'
if (plan['limits']!=dict(wall_seconds=600,sampled_rss_bytes=768*1024**2,storage_bytes=128*1024**2)
        or plan['basetemp']!=expected_base or plan['path_roots']!=[str(REPO),str(Path(expected_base))]
        or plan['pytest_target']!='tests/test_h1_hour0_n0_source_cost_development_v1.py::test_closed_owned_n0_original_source_cost'
        or plan['attempts']!=1 or plan['synthetic_jobs']!=1 or plan['original_source_prepares']!=1
        or Path(plan['inner_output'])!=HERE/'fresh_owned_source_cost_01_non_authoritative'
        or Path(plan['outer_output'])!=HERE/'fresh_owned_source_cost_monitor_01'):
    raise ValueError('fixed source-cost scope, roots, target or limits differ')
if any(Path(plan[key]).exists() for key in ('inner_output','outer_output','basetemp')):
    raise ValueError('fresh source-cost roots required; preserve existing artifacts')
out=Path(plan['outer_output']);out.mkdir(exist_ok=False)
command=[sys.executable,'-I','-B',str(HERE/'run_n0_path_entry_v1.py'),plan_name,expected_plan_pin]
sources=plan['source_sha256'];old_pins=plan['old_chain_sha256']
owned={};events=[];errors=[];peak=storage=0;reason=None;proc=None;result={};start=time.monotonic()
def save(name,value):
    with (out/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
def live(pid,created):
    try:
        p=psutil.Process(pid);return p if p.create_time()==created and p.is_running() else None
    except psutil.Error:return None
def observe():
    for pid,created in tuple(owned.items()):
        p=live(pid,created)
        if p is None:continue
        try:
            for child in p.children(recursive=True):owned[child.pid]=child.create_time()
        except psutil.Error:pass
    return [p for pid,created in tuple(owned.items()) if (p:=live(pid,created)) is not None]
def cleanup():
    deadline=time.monotonic()+8
    while True:
        active=observe()
        if not active:break
        for p in active:
            try:p.kill();events.append(dict(pid=p.pid,creation_time=owned[p.pid]))
            except psutil.NoSuchProcess:pass
            except psutil.Error as error:errors.append(repr(error))
        psutil.wait_procs(active,timeout=min(.5,max(0,deadline-time.monotonic())))
        if time.monotonic()>=deadline:break
    remaining=[dict(pid=p.pid,creation_time=owned[p.pid]) for p in observe()]
    result.update(observed_owned_processes=[dict(pid=p,creation_time=c) for p,c in owned.items()],
        observed_owned_processes_remaining=remaining,observed_owned_processes_absent=not remaining,cleanup_events=events)
try:
    for path,pin in {**sources,**old_pins}.items():
        if sha256(Path(path).read_bytes()).hexdigest()!=pin:raise ValueError('fixed source or old-chain input differs')
    for name in sources:
        path=Path(name);relative=path.relative_to(REPO) if path.is_relative_to(REPO) else Path('vendor')/path.relative_to(Path('D:/'))
        target=out/'tested_bytes'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes())
    save('request.json',dict(plan,command=command,plan_sha256=sha256(plan_raw).hexdigest()))
    with (out/'stdout.log').open('x',encoding='utf-8') as stream:
        proc=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,cwd=REPO)
        owned[proc.pid]=psutil.Process(proc.pid).create_time();save('started.json',dict(pid=proc.pid,creation_time=owned[proc.pid]))
        next_storage=next_heartbeat=0
        while proc.poll() is None:
            elapsed=time.monotonic()-start;rss=0
            for p in observe():
                try:rss+=p.memory_info().rss
                except psutil.Error:pass
            peak=max(peak,rss)
            if elapsed>=next_storage:
                storage=sum(p.stat().st_size for root in (out,Path(plan['inner_output']),Path(plan['basetemp']))
                    if root.exists() for p in root.rglob('*') if p.is_file());next_storage=elapsed+1
            if elapsed>=next_heartbeat:
                with (out/'heartbeat.jsonl').open('a',encoding='utf-8') as hb:
                    hb.write(json.dumps(dict(seconds=elapsed,observed_tree_rss=rss,observed_storage_bytes=storage))+'\n')
                next_heartbeat=elapsed+15
            if elapsed>600 or rss>1024**3 or storage>128*1024**2:
                reason='wall' if elapsed>600 else 'rss' if rss>1024**3 else 'storage';break
            time.sleep(.1)
        if reason is not None:cleanup()
        result['child_exit_code']=proc.wait(timeout=10)
except BaseException:errors.append(traceback.format_exc())
finally:
    cleanup()
    for label,pins in (('source',sources),('old_chain',old_pins)):
        try:
            drift=[p for p,h in pins.items() if not Path(p).is_file() or sha256(Path(p).read_bytes()).hexdigest()!=h]
            result[label+'_unchanged']=not drift;result[label+'_drift']=drift
        except BaseException:errors.append(traceback.format_exc())
    lock_rows=[]
    for path in sorted(Path(plan['basetemp']).rglob('*.lock')):
        try:
            with path.open('r+b',buffering=0) as stream:
                stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
                try:lock_rows.append(str(path))
                finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
        except BaseException:errors.append(traceback.format_exc())
    inner=Path(plan['inner_output'])/'terminal.json'
    if inner.is_file():result['inner_terminal_sha256']=sha256(inner.read_bytes()).hexdigest();result['inner_exit_code']=json.loads(inner.read_bytes())['exit_code']
    result.update(stop_reason=reason,elapsed_seconds=time.monotonic()-start,peak_observed_process_tree_rss=peak,
        observed_storage_bytes=storage,memory_is_sampled=True,saved_locks_reacquired_and_released=lock_rows,errors=errors,
        formal_result=False,resource_admission=False,full_hour0_chain_passed=False,native_execution_authorized=False)
    result['exit_code']=0 if (not errors and reason is None and result.get('child_exit_code')==result.get('inner_exit_code')==0
        and result['observed_owned_processes_absent'] and result.get('source_unchanged') and result.get('old_chain_unchanged')) else 1
    save('terminal.json',result);print(json.dumps(result),flush=True)
sys.exit(result['exit_code'])
