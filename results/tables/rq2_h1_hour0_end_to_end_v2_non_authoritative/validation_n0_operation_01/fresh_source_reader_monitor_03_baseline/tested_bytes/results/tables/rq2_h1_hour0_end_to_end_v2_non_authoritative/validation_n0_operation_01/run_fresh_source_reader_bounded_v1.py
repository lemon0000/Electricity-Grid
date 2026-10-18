"""One externally pinned reader diagnostic over completed, owned synthetic input."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

import psutil

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
mode,pin=sys.argv[1:]
if mode not in ('baseline','candidate'):raise ValueError('fixed reader mode required')
plan_name=f'fresh_source_reader_plan_03_{mode}.json'
raw=(HERE/plan_name).read_bytes()
if sha256(raw).hexdigest()!=pin:raise ValueError('external plan SHA differs')
plan=json.loads(raw)
limits=dict(wall_seconds=120,sampled_rss_bytes=768*1024**2,storage_bytes=128*1024**2)
expected_reader='bounded_stable_read_entry_v2.py' if mode=='baseline' else 'bounded_stable_read_entry_v3.py'
if (plan['mode']!=mode or plan['limits']!=limits or plan['reader_entry']!=expected_reader
        or plan['original_source_prepares']!=1 or plan['synthetic_jobs']!=0
        or plan['path_roots']!=[str(REPO),str(Path('D:/h1_fresh_owned_source_cost_03_non_authoritative'))]
        or Path(plan['inner_output'])!=HERE/f'fresh_source_reader_03_{mode}_non_authoritative'
        or Path(plan['outer_output'])!=HERE/f'fresh_source_reader_monitor_03_{mode}'
        or Path(plan['fixture_base'])!=Path(f'D:/h1_source_reader_03_{mode}_non_authoritative')):
    raise ValueError('fixed reader scope or resource limits differ')
if any(os.path.lexists(plan[k]) for k in ('inner_output','outer_output','fixture_base')):
    raise ValueError('new output/fixture roots required; retain prior attempts')


def baseline_admission():
    if mode=='baseline':return {}
    baseline_raw=(HERE/'fresh_source_reader_plan_03_baseline.json').read_bytes()
    expected=plan['baseline_plan_sha256']
    if sha256(baseline_raw).hexdigest()!=expected:raise ValueError('fixed baseline plan differs')
    baseline=json.loads(baseline_raw)
    for key in ('source_sha256','saved_sha256','old_chain_sha256','code_lease_sha256','path_roots',
            'saved_source_cost_report','saved_source_audit_path','saved_source_fields_path',
            'expected_decision_bytes_sha256','expected_normal_decision_identity',
            'expected_audit_sha256','expected_complete_projection_sha256'):
        if baseline[key]!=plan[key]:raise ValueError('reader pair input or oracle differs')
    folder=Path(baseline['outer_output'])
    request_raw=(folder/'request.json').read_bytes();request=json.loads(request_raw)
    terminal_raw=(folder/'terminal.json').read_bytes();terminal=json.loads(terminal_raw)
    if ({key:request.get(key) for key in baseline}!=baseline or request['plan_sha256']!=expected
            or terminal['exit_code']!=0 or terminal['child_exit_code']!=0 or terminal['inner_exit_code']!=0
            or terminal['stop_reason'] is not None or terminal['errors']
            or not terminal['observed_owned_processes_absent']
            or not all(terminal[key+'_unchanged'] for key in ('source','saved','old_chain'))
            or sha256((Path(baseline['inner_output'])/'terminal.json').read_bytes()).hexdigest()!=terminal['inner_terminal_sha256']):
        raise ValueError('successful exact baseline terminal required before candidate')
    return dict(baseline_plan_sha256=expected,baseline_request_sha256=sha256(request_raw).hexdigest(),
        baseline_terminal_sha256=sha256(terminal_raw).hexdigest())


baseline_evidence=baseline_admission()
out=Path(plan['outer_output']);out.mkdir(exist_ok=False)
owned={};errors=[];process_errors=set();events=[];result={};peak=0;reason=None;proc=None;start=time.monotonic()


def save(name,value):
    with (out/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)


def live(pid,created):
    try:
        p=psutil.Process(pid);return p if p.create_time()==created and p.is_running() else None
    except psutil.NoSuchProcess:return None
    except psutil.Error as error:process_errors.add(repr(error));return None


def observe():
    for pid,created in tuple(owned.items()):
        p=live(pid,created)
        if p is not None:
            try:
                for child in p.children(recursive=True):owned[child.pid]=child.create_time()
            except psutil.NoSuchProcess:pass
            except psutil.Error as error:process_errors.add(repr(error))
    return [p for pid,created in tuple(owned.items()) if (p:=live(pid,created)) is not None]


def cleanup():
    deadline=time.monotonic()+8
    while active:=observe():
        for p in active:
            try:p.kill();events.append(dict(pid=p.pid,creation_time=owned[p.pid]))
            except psutil.NoSuchProcess:pass
            except psutil.Error as error:errors.append(repr(error))
        try:psutil.wait_procs(active,timeout=.2)
        except psutil.Error as error:process_errors.add(repr(error))
        if time.monotonic()>=deadline:break
    if proc is not None:
        try:
            if proc.poll() is None:proc.kill();events.append(dict(pid=proc.pid,exact_popen_handle_fallback=True))
            proc.wait(timeout=10)
        except BaseException:errors.append(traceback.format_exc())
    result.update(observed_owned_processes=[dict(pid=p,creation_time=c) for p,c in owned.items()],
        observed_owned_processes_absent=not observe() and not process_errors,
        process_observation_errors=sorted(process_errors),cleanup_events=events)


def storage():
    return sum(p.stat().st_size for root in (out,Path(plan['inner_output']),Path(plan['fixture_base']))
        if root.exists() for p in root.rglob('*') if p.is_file())


def resource_rss():
    rss=0
    for p in observe():
        try:rss+=p.memory_info().rss
        except psutil.NoSuchProcess:pass
        except psutil.Error as error:process_errors.add(repr(error))
    if process_errors:raise RuntimeError('process resource observation failed: '+repr(sorted(process_errors)))
    return rss


try:
    for name,digest in {**plan['source_sha256'],**plan['saved_sha256'],**plan['old_chain_sha256']}.items():
        if sha256(Path(name).read_bytes()).hexdigest()!=digest:raise ValueError('fixed input differs: '+name)
    for row in plan['completed_input_owned_processes']:
        if live(row['pid'],row['creation_time']) is not None:raise ValueError('completed input process is still active')
    if process_errors:raise RuntimeError('completed input process observation failed')
    for name in plan['source_sha256']:
        path=Path(name);relative=path.relative_to(REPO) if path.is_relative_to(REPO) else Path('vendor')/path.relative_to(Path('D:/'))
        target=out/'tested_bytes'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes())
    command=[sys.executable,'-I','-B',str(HERE/'measure_fresh_source_reader_v1.py'),plan_name,pin]
    save('request.json',dict(plan,command=command,plan_sha256=pin,baseline_admission=baseline_evidence))
    with (out/'stdout.log').open('x',encoding='utf-8') as stream:
        proc=subprocess.Popen(command,cwd=REPO,stdout=stream,stderr=subprocess.STDOUT)
        owned[proc.pid]=psutil.Process(proc.pid).create_time();save('started.json',dict(pid=proc.pid,creation_time=owned[proc.pid]))
        next_sample=0;used=0
        while proc.poll() is None:
            elapsed=time.monotonic()-start
            rss=resource_rss();peak=max(peak,rss)
            if elapsed>=next_sample:used=storage();next_sample=elapsed+1
            if elapsed>120 or rss>limits['sampled_rss_bytes'] or used>limits['storage_bytes']:
                reason='wall' if elapsed>120 else 'rss' if rss>limits['sampled_rss_bytes'] else 'storage'
                cleanup();break
            time.sleep(.1)
        result['child_exit_code']=proc.wait(timeout=10)
except BaseException:errors.append(traceback.format_exc())
finally:
    cleanup()
    for label,key in (('source','source_sha256'),('saved','saved_sha256'),('old_chain','old_chain_sha256')):
        drift=[name for name,pin in plan[key].items() if not Path(name).is_file() or sha256(Path(name).read_bytes()).hexdigest()!=pin]
        result[label+'_unchanged']=not drift;result[label+'_drift']=drift
    terminal=Path(plan['inner_output'])/'terminal.json'
    if terminal.is_file():
        result['inner_exit_code']=json.loads(terminal.read_bytes())['exit_code']
        result['inner_terminal_sha256']=sha256(terminal.read_bytes()).hexdigest()
    result.update(errors=errors,stop_reason=reason,elapsed_seconds=time.monotonic()-start,
        peak_observed_process_tree_rss=peak,memory_is_sampled=True,observed_storage_bytes=0,
        external_input_writer_locks_probed=False,synthetic_jobs=0,real_native_calls=0,
        formal_result=False,resource_admission=False,full_hour0_chain_passed=False,native_execution_authorized=False)
    result['exit_code']=0 if (not errors and reason is None and result.get('child_exit_code')==result.get('inner_exit_code')==0
        and result['observed_owned_processes_absent'] and all(result[k+'_unchanged'] for k in ('source','saved','old_chain'))) else 1
    used=storage()
    for _ in range(10):
        encoded=json.dumps(result,indent=2).encode('utf-8');total=used+len(encoded)
        if total>limits['storage_bytes'] and (result['exit_code']!=1 or result['stop_reason']!='storage'):
            result.update(exit_code=1,stop_reason='storage');continue
        if total==result['observed_storage_bytes']:break
        result['observed_storage_bytes']=total
    else:raise ValueError('terminal size accounting failed')
    with (out/'terminal.json').open('xb') as stream:stream.write(encoded)
    if storage()!=result['observed_storage_bytes']:raise ValueError('terminal size readback failed')
    print(json.dumps(result),flush=True)
raise SystemExit(result['exit_code'])
