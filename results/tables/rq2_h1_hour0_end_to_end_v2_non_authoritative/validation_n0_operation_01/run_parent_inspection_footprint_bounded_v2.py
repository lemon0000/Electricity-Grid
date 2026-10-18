"""One fixed zero-Job hotpath diagnostic with observed process identity and final cleanup."""
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
plan_raw=(HERE/'parent_inspection_footprint_plan_02.json').read_bytes();plan=json.loads(plan_raw)
out=Path(plan['outer_output']);out.mkdir(exist_ok=False)
command=[sys.executable,'-I','-B',str(HERE/'measure_parent_inspection_footprint_v2.py'),sha256(plan_raw).hexdigest()]
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
            if (elapsed>plan['limits']['wall_seconds'] or rss>plan['limits']['sampled_rss_bytes'] or storage>plan['limits']['storage_bytes']):
                reason='wall' if elapsed>plan['limits']['wall_seconds'] else 'rss' if rss>plan['limits']['sampled_rss_bytes'] else 'storage';break
            time.sleep(.1)
        if reason is not None:cleanup()
        result['child_exit_code']=proc.wait(timeout=10)
except BaseException:errors.append(traceback.format_exc())
finally:
    if proc is not None and proc.poll() is None:
        try:proc.kill();proc.wait(timeout=10)
        except BaseException:errors.append(traceback.format_exc())
    cleanup()
    for label,pins in (('source',sources),('old_chain',old_pins)):
        try:
            drift=[p for p,h in pins.items() if not Path(p).is_file() or sha256(Path(p).read_bytes()).hexdigest()!=h]
            result[label+'_unchanged']=not drift;result[label+'_drift']=drift
        except BaseException:errors.append(traceback.format_exc())
    try:
        saved_actual={}
        for name in plan['saved_inventory_roots']:
            root=Path(name)
            for p in (root.rglob('*') if root.is_dir() else (root,)):
                if p.is_file() and p.suffix != '.lock':saved_actual[str(p)]=sha256(p.read_bytes()).hexdigest()
        saved_drift=[p for p in saved_actual.keys()|plan['saved_sha256'].keys()
            if saved_actual.get(p)!=plan['saved_sha256'].get(p)]
        result.update(saved_files_unchanged=not saved_drift,saved_drift=saved_drift,
            saved_file_count=len(saved_actual))
    except BaseException:
        result['saved_files_unchanged']=False;errors.append(traceback.format_exc())
    lock_rows=[]
    lock_paths=set(Path(plan['basetemp']).rglob('*.lock'))
    result['externally_owned_input_locks_not_touched']=True
    for path in sorted(lock_paths):
        try:
            with path.open('r+b',buffering=0) as stream:
                stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
                try:lock_rows.append(str(path))
                finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
        except BaseException:errors.append(traceback.format_exc())
    if sum(Path(p).is_relative_to(Path(plan['saved_root'])) for p in lock_rows)!=plan['expected_saved_locks']:
        errors.append('complete saved-root lock set was not reacquired')
    inner=Path(plan['inner_output'])/'terminal.json'
    if inner.is_file():result['inner_terminal_sha256']=sha256(inner.read_bytes()).hexdigest();result['inner_exit_code']=json.loads(inner.read_bytes())['exit_code']
    result.update(stop_reason=reason,elapsed_seconds=time.monotonic()-start,peak_observed_process_tree_rss=peak,
        observed_storage_bytes=storage,memory_is_sampled=True,saved_locks_reacquired_and_released=lock_rows,errors=errors,
        formal_result=False,resource_admission=False,full_hour0_chain_passed=False,native_execution_authorized=False)
    result['exit_code']=0 if (not errors and reason is None and result.get('child_exit_code')==result.get('inner_exit_code')==0
        and result['observed_owned_processes_absent'] and result.get('source_unchanged') and result.get('old_chain_unchanged') and result.get('saved_files_unchanged')) else 1
    save('terminal.json',result);print(json.dumps(result),flush=True)
sys.exit(result['exit_code'])
