"""Observed limits for local development checks; no formal resource authority."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

import psutil


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SLICE_BASE=None
start=time.monotonic()
label, seconds, ram_mib, storage_mib, *arguments = sys.argv[1:]
if not label.replace('_', '').isalnum() or not arguments or arguments.pop(0) != '--':
    raise ValueError('unique label, limits and explicit command arguments required')
limit, ram, storage_cap = float(seconds), int(ram_mib) * 1024**2, int(storage_mib) * 1024**2
if not 0 < limit <= 2100 or not 0 < ram <= 1024**3 or not 0 < storage_cap <= 128 * 1024**2:
    raise ValueError('bounded development limits exceeded')
command = [sys.executable, '-B', *arguments]
attempt=HERE/'chain_07'
plan_path=attempt/'postcheck_supplement_plan_02.json'
plan=json.loads(plan_path.read_bytes())
expected_command=[str(HERE/'postcheck_complete_v2_resume.py'),'chain_07']
if [str((REPO/arguments[0]).resolve()),*arguments[1:]]!=expected_command:
    raise ValueError('fixed completed-chain postcheck continuation required')
if label!='postcheck_supplement_monitor_02' or limit!=2100:
    raise ValueError('fixed one-attempt postcheck plan required')
artifact_root=Path(plan['input_root'])
if artifact_root.resolve()!=Path('D:/h1_chain_07_non_authoritative').resolve():
    raise ValueError('fixed closed-chain input root required')
for name,pin in {**plan['input_files_sha256'],**plan['helper_files_sha256']}.items():
    if sha256(Path(name).read_bytes()).hexdigest()!=pin:raise ValueError('planned postcheck input changed')
for p in ('postcheck_supplement_04_non_authoritative',):
    if (attempt/p).exists():raise ValueError('postcheck attempt root must be fresh')
terminal=json.loads((attempt/'terminal.json').read_bytes())
if (terminal['exit_code']!=0 or terminal['before']!=terminal['after']
        or sha256((attempt/'terminal.json').read_bytes()).hexdigest()!=plan['chain_terminal_sha256']):
    raise ValueError('successful immutable terminal required')
out=attempt/label
if out.exists():raise ValueError('fresh outer attempt required')
storage_roots=[out,attempt/'postcheck_supplement_04_non_authoritative']
out.mkdir(exist_ok=False)



def save(name, value):
    with (out / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2)


source_pins={};source_snapshot_complete=False

def snapshot_sources():
    global source_pins,source_snapshot_complete
    import importlib.util
    sources={Path(__file__).resolve(),plan_path,*(Path(n) for n in plan['input_files_sha256']),
        *(Path(n) for n in plan['helper_files_sha256']),*(REPO/n for n in terminal['after'])}
    sources.update(attempt/n for n in ('request.json','started.json','terminal.json','stdout.log','stderr.log','timing.jsonl'))
    auxiliary=json.loads((HERE/'preservation_check_02.json').read_bytes())['static_tests_closure']
    sources.update(REPO/n for n in auxiliary)
    sources.add(REPO/'results/tables/rq2_v2_obligation_manifest_v1_non_authoritative/obligation_manifest_v2_final.json')
    pygments=Path(importlib.util.find_spec('pygments').origin).resolve()
    sources.update(pygments.parent.rglob('*.py'))
    source_pins = {str(p): sha256(p.read_bytes()).hexdigest() for p in sources}
    for path in sources:
        destination = (out/'tested_bytes'/path.relative_to(REPO) if path.is_relative_to(REPO)
            else out/'tested_bytes/external'/path.drive[:1]/Path(*path.parts[1:]))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
    save('request.json', dict(command=command, seconds=limit, sampled_rss_cap_bytes=ram,
        storage_cap_bytes=storage_cap, storage_roots=list(map(str, storage_roots)),
        source_sha256=source_pins,
        runner_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        formal_result=False, resource_admission=False))
    source_snapshot_complete=True

peak = storage = 0
reason = None
proc = target = None
result = {}
owned={};events=[];errors=[]
def live(pid,created):
    try:
        p=psutil.Process(pid)
        return p if p.create_time()==created and p.is_running() else None
    except psutil.NoSuchProcess:return None
    except psutil.Error as error:
        errors.append(dict(stage='process_identity',pid=pid,error=repr(error)));return None

def observe():
    for pid,created in tuple(owned.items()):
        p=live(pid,created)
        if p is None:continue
        try:
            for child in p.children(recursive=True):owned[child.pid]=child.create_time()
        except psutil.NoSuchProcess:pass
        except psutil.Error as error:errors.append(dict(stage='discover',pid=pid,error=repr(error)))
    return [p for pid,created in tuple(owned.items()) if (p:=live(pid,created)) is not None]

def finish_children():
    deadline=time.monotonic()+8
    while True:
        active=observe()
        if not active:break
        for p in active:
            try:p.kill();events.append(dict(pid=p.pid,creation_time=owned[p.pid],action='kill_owned'))
            except psutil.NoSuchProcess:pass
            except psutil.Error as error:errors.append(dict(stage='kill',error=repr(error),pid=p.pid))
        try:psutil.wait_procs(active,timeout=min(0.5,max(0,deadline-time.monotonic())))
        except psutil.Error as error:errors.append(dict(stage='wait',error=repr(error)))
        if time.monotonic()>=deadline:break
    remaining=[dict(pid=p.pid,creation_time=owned[p.pid]) for p in observe()]
    result.update(observed_owned_processes=[dict(pid=p,creation_time=c) for p,c in owned.items()],
        observed_owned_processes_remaining=remaining,observed_owned_processes_absent=not remaining,
        process_cleanup_scope='PID plus creation time; repeated observed-descendant discovery',cleanup_events=events)
    result['descendant_discovery_complete']=not any(row.get('stage') in ('discover','process_identity') for row in errors)
    result['complete_process_tree_absence_proven']=False
    if remaining:result['exit_code']=1


def storage_observation():
    total=0;failures=[]
    for root in storage_roots:
        try:
            root.stat()
            def failed(error):failures.append(dict(path=error.filename,error=repr(error)))
            for directory,_,names in os.walk(root,onerror=failed,followlinks=False):
                for name in names:
                    path=Path(directory)/name
                    try:total+=path.stat(follow_symlinks=False).st_size
                    except OSError as error:failures.append(dict(path=str(path),error=repr(error)))
        except FileNotFoundError:continue
        except OSError as error:failures.append(dict(path=str(root),error=repr(error)))
    return total,failures


def include_terminal_storage(value,prior_bytes,cap):
    # Include this terminal's own bytes in the final cap, including the digits
    # of the resulting size field. No partially published terminal is edited.
    for _ in range(12):
        size=prior_bytes+len(json.dumps(value,indent=2).encode('utf-8'))
        if size>cap:
            value['exit_code']=1;value['stop_reason']=value.get('stop_reason') or 'storage'
        if value.get('observed_storage_bytes')==size:return value
        value['observed_storage_bytes']=size
    raise ValueError('terminal storage accounting did not converge')


def emergency_parent_stop():
    # Popen retains the exact direct-child handle even if psutil identity or
    # descendant discovery fails. Never wait indefinitely on the failed probe.
    if proc is None:return
    if proc.poll() is None:
        try:proc.kill()
        except OSError as error:errors.append(dict(stage='direct_child_kill',error=repr(error)))
    try:proc.wait(timeout=8)
    except subprocess.TimeoutExpired as error:errors.append(dict(stage='direct_child_wait',error=repr(error)))

try:
    snapshot_sources()
    with (out / 'stdout.log').open('x', encoding='utf-8') as stream:
        proc = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)
        target = psutil.Process(proc.pid)
        owned[proc.pid]=target.create_time()
        save('started.json', dict(pid=proc.pid, creation_time=owned[proc.pid]))
        next_storage = 0
        while proc.poll() is None:
            elapsed = time.monotonic() - start
            try:
                processes = observe()
                if errors:raise RuntimeError('process discovery incomplete')
                rss = psutil.Process().memory_info().rss+sum(p.memory_info().rss for p in processes if p.is_running())
                peak = max(peak, rss)
            except psutil.NoSuchProcess:
                rss = 0
            except psutil.Error as error:
                errors.append(dict(stage='process_rss',error=repr(error)))
                reason='process_read_error';finish_children();emergency_parent_stop();break
            if elapsed >= next_storage:
                storage,storage_errors=storage_observation()
                if storage_errors:
                    errors.extend(storage_errors);reason='storage_read_error';finish_children();break
                next_storage = elapsed + 1
            if elapsed > limit or rss > ram or storage > storage_cap:
                reason = 'wall' if elapsed > limit else 'rss' if rss > ram else 'storage'
                finish_children()
                break
            time.sleep(0.1)
        result['exit_code'] = proc.wait(timeout=8)
except BaseException:
    result.update(exit_code=None, error=traceback.format_exc())
    try:finish_children()
    finally:emergency_parent_stop()
finally:
    finish_children()
    emergency_parent_stop()
    storage,storage_errors=storage_observation()
    errors.extend(storage_errors)
    if storage_errors or storage>storage_cap:
        reason=reason or ('storage_read_error' if storage_errors else 'storage')
        result['exit_code']=1
    result.update(storage_read_errors=storage_errors,cleanup_errors=errors,
        final_storage_observation_complete=not storage_errors)
    if errors:result['exit_code']=1
    drift=[]
    for name,pin in source_pins.items():
        try:
            if sha256(Path(name).read_bytes()).hexdigest()!=pin:drift.append(name)
        except OSError as error:
            drift.append(name);errors.append(dict(stage='source_postcheck',path=name,error=repr(error)))
    if drift:
        result.update(exit_code=1, source_drift=drift)
    membership={str(p) for p in artifact_root.rglob('*') if p.is_file()}
    result['artifact_membership_unchanged']=membership==set(plan['input_files_sha256'])
    if not result['artifact_membership_unchanged']:
        result.update(exit_code=1,stop_reason=reason or 'artifact_membership')
    result.update(elapsed_seconds=time.monotonic() - start, stop_reason=reason,
        peak_observed_process_tree_rss=peak, observed_storage_bytes=storage,
        memory_is_sampled=True, source_unchanged=not drift and source_snapshot_complete,
        source_snapshot_complete=source_snapshot_complete,
        peak_rss_includes_monitor=True,
        formal_result=False, resource_admission=False)
    result=include_terminal_storage(result,storage,storage_cap)
    save('terminal.json', result)
    print(json.dumps(result), flush=True)
sys.exit(0 if result.get('exit_code') == 0 and reason is None else 1)
