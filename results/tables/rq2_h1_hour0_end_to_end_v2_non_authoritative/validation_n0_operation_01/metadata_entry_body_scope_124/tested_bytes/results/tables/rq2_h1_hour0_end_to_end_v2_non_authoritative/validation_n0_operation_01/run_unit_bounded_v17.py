"""Observed limits for local development checks; no formal resource authority."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import stat
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
unit_entry=(HERE/'run_unit_entry_v4.py').resolve(strict=True)
if not arguments or (REPO/arguments[0]).resolve(strict=True)!=unit_entry:
    raise ValueError('explicit ordinary unit entry required')
if '--basetemp' not in arguments or '-p' not in arguments or 'no:faulthandler' not in arguments:
    raise ValueError('fresh root and disabled C faulthandler required')
base=Path(arguments[arguments.index('--basetemp')+1])
if not base.is_absolute() or not base.name.endswith('_non_authoritative') or os.path.lexists(base):
    raise ValueError('unused absolute non-authoritative test root required')
selected=[p.split('::',1)[0] for p in arguments[1:] if p.split('::',1)[0].endswith('.py')]
if not selected or any(not p.startswith('tests/test_h1_') for p in selected):
    raise ValueError('explicit H1 unit files required')
if any('hour0_end_to_end' in p or 'guarded_common_slice' in p for p in selected):
    raise ValueError('whole integration requires its separate performance plan')
entry=(HERE.parent/'validation_path_optimization_01/entry_revision_07').resolve(strict=True)
out=HERE/label
if os.path.lexists(out):raise ValueError('fresh outer attempt root required')
storage_roots=[out,base]
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
    sources.update((REPO/'experiments').glob('h1_*.py'))
    sources.update((REPO/'tests').glob('*.py'))
    sources.add(unit_entry)
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


def storage_observation(*,final=False):
    total=0;failures=[]
    for root in storage_roots:
        try:
            observed=root.stat(follow_symlinks=False)
            if not stat.S_ISDIR(observed.st_mode) or getattr(observed,'st_file_attributes',0)&0x400:
                raise ValueError('ordinary non-reparse storage root required')
            pending=[root]
            while pending:
                directory=pending.pop()
                try:
                    observed=directory.stat(follow_symlinks=False)
                    if not stat.S_ISDIR(observed.st_mode) or getattr(observed,'st_file_attributes',0)&0x400:
                        raise ValueError('ordinary non-reparse storage directory required')
                    with os.scandir(directory) as entries:
                        for entry in entries:
                            try:
                                info=entry.stat(follow_symlinks=False)
                                if stat.S_ISDIR(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400:
                                    pending.append(Path(entry.path))
                                else:total+=info.st_size
                            except OSError as error:failures.append(dict(path=entry.path,error=repr(error)))
                except (OSError,ValueError) as error:failures.append(dict(path=str(directory),error=repr(error)))
        except FileNotFoundError as error:
            if final or root!=base:failures.append(dict(path=str(root),error=repr(error)))
        except (OSError,ValueError) as error:failures.append(dict(path=str(root),error=repr(error)))
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
    storage,storage_errors=storage_observation(final=True)
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
        storage_observation_contract='observed_entries_nonfollow_with_directory_rechecks',storage_path_ABA_covered=False,
        memory_is_sampled=True, source_unchanged=not drift and source_snapshot_complete,
        source_snapshot_complete=source_snapshot_complete,
        peak_rss_includes_monitor=True,
        formal_result=False, resource_admission=False)
    result=include_terminal_storage(result,storage,storage_cap)
    result['request_sha256']=sha256((out/'request.json').read_bytes()).hexdigest() if (out/'request.json').exists() else None
    result['started_sha256']=sha256((out/'started.json').read_bytes()).hexdigest() if (out/'started.json').exists() else None
    result['runner_sha256']=sha256(Path(__file__).read_bytes()).hexdigest()
    result['unit_entry_sha256']=sha256(unit_entry.read_bytes()).hexdigest()
    save('terminal.json', result)
    print(json.dumps(result), flush=True)
sys.exit(0 if result.get('exit_code') == 0 and reason is None else 1)
