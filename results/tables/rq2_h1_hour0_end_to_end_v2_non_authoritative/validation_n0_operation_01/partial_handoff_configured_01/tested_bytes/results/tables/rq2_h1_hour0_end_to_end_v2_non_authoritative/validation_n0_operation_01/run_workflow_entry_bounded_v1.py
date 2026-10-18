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
ENTRY_ROOT=HERE.parent/'validation_path_optimization_01/entry_revision_08_non_authoritative'
REPO = HERE.parents[3]
SLICE_BASE=None
start=time.monotonic()
label, seconds, ram_mib, storage_mib, *arguments = sys.argv[1:]
if not label.replace('_', '').isalnum() or not arguments or arguments.pop(0) != '--':
    raise ValueError('unique label, limits and explicit command arguments required')
limit, ram, storage_cap = float(seconds), int(ram_mib) * 1024**2, int(storage_mib) * 1024**2
if not 0 < limit <= 600 or not 0 < ram <= 1024**3 or not 0 < storage_cap <= 128 * 1024**2:
    raise ValueError('bounded development limits exceeded')
command = [sys.executable, '-B', *arguments]
if len(arguments)<5 or arguments[0]!='-I':
    raise ValueError('explicit configured-entry invocation required')
launcher=(REPO/arguments[1]).resolve(strict=True)
entry=ENTRY_ROOT.resolve(strict=True)
if launcher!=entry/'launch_validation.py' or not arguments[4].replace('_','').isalnum():
    raise ValueError('fixed draft entry and unique child attempt label required')
kind,mode,child_label,*targets=arguments[2:]
allowed={
 'tests/test_h1_selector_parent_controller_development_v3.py::test_actual_lifecycle_clears_each_external_boundary_and_binds_plain_receipts',
 'tests/test_h1_selector_parent_controller_development_v3.py',
 'tests/test_h1_selector_source_window_development_v1.py',
 'tests/test_h1_selector_parent_validation_operation_development_v3.py',
 'tests/test_h1_selector_post_negative_validation_development_v2.py',
 'tests/test_h1_common_validation_operation_development_v3.py',
 'tests/test_h1_selector_phase_handoff_development_v5.py',
 'tests/test_h1_repair_cap_normalization_operation_development_v1.py',
}
if kind=='unit':
    if mode!='parse' or targets or limit>180:raise ValueError('bounded entry unit role required')
elif kind=='pytest':
    if mode!='parse_path' or not targets or any(t not in allowed for t in targets):
        raise ValueError('bounded zero-Job successor unit targets required')
else:raise ValueError('ordinary unit checks only; whole integration needs its completed performance plan')
slice_role=kind=='pytest'
if slice_role:
    SLICE_BASE=Path('D:/h1_wf08_'+child_label+'_non_authoritative')
    if SLICE_BASE.exists():raise ValueError('unused short unit root required')
out=HERE/label
child_output=entry/child_label
if out.exists() or child_output.exists():raise ValueError('fresh outer and child attempt roots required')
storage_roots=[out,child_output]+([SLICE_BASE] if kind=='pytest' and slice_role else [])
out.mkdir(exist_ok=False)



def save(name, value):
    with (out / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2)


source_pins={};source_snapshot_complete=False

def snapshot_sources():
    global source_pins,source_snapshot_complete
    sources = {Path(__file__).resolve(), REPO / 'experiments/h1_canonical_path_lease_development_v1.py',
        REPO / 'tests/test_h1_canonical_path_lease_development_v1.py'}
    sources.update(p for p in entry.iterdir() if p.is_file())
    sources.update(Path(name) for name in json.loads((entry/'code_allowlist_v3.json').read_bytes())['files_sha256'])
    sources.update(REPO/name for name in json.loads((entry/'test_closure_v1.json').read_bytes())['files_sha256'])
    vendor_manifest=entry/'vendor_code_allowlist_v1.json'
    sources.add(vendor_manifest)
    sources.update(Path(name) for name in json.loads(vendor_manifest.read_bytes())['files_sha256'])
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
