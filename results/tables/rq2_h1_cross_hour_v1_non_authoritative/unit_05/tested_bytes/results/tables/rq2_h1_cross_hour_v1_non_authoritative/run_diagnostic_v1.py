"""Bounded whole-path synthetic diagnostic; keeps successful and failed roots."""
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
label, mode = sys.argv[1:]
if not label.replace('_', '').isalnum() or mode not in ('units', 'units_tail', 'connected'):
    raise ValueError('fresh label and explicit diagnostic scope required')
out = HERE/label
base = Path('D:/')/f'h1_cross_{label}_non_authoritative'
if out.exists() or base.exists():
    raise ValueError('diagnostic roots must be fresh')
out.mkdir()
seconds = 600 if mode == 'connected' else 120
rss_cap, disk_cap = 1024*1024**2, 128*1024**2
test = 'tests/test_h1_cross_hour_owner_development_v1.py'
if mode == 'connected':
    selected = [test+'::test_two_hour_three_lane_connected_chain']
elif mode == 'units':
    selected = [test, '-k', 'not two_hour_three_lane_connected_chain']
else:
    selected = [test, '-k', 'aggregate or selector_callable or selector_dispatch or selector_purpose or normal_reports or normal_failure or reference_failure or business_unresolved or static_identity_cache']
entry = REPO/'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_n0_operation_01/run_unit_entry_v6.py'
command = [sys.executable, '-u', '-B', str(entry), '-s', '-p', 'no:faulthandler',
           '--basetemp', str(base), '--junitxml', str(out/'junit.xml'), *selected]
sources = set((REPO/'src').rglob('*.py')) | set((REPO/'experiments').glob('h1_*.py'))
sources |= set((REPO/'experiments').glob('rq2_v2_*.py')) | set((REPO/'tests').glob('*.py'))
sources |= {Path(__file__), HERE/'performance_review.md', entry,
    REPO/'configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml',
    REPO/'configs/rq2_normal_h1_calibration_v3.json'}
pins = {str(path): sha256(path.read_bytes()).hexdigest() for path in sorted(sources)}
for name in pins:
    path = Path(name)
    destination = out/'tested_bytes'/path.relative_to(REPO)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(path.read_bytes())


def save(name, body):
    with (out/name).open('x', encoding='utf-8') as stream:
        json.dump(body, stream, indent=2)
        stream.write('\n')


save('request.json', dict(command=command, seconds=seconds, no_progress_seconds=120,
    sampled_tree_rss_cap_bytes=rss_cap, logical_storage_cap_bytes=disk_cap,
    base=str(base), sources_sha256=pins, python=sys.version, executable=sys.executable,
    mode=mode, diagnostic_only=True, formal_result=False, native_calls_authorized=False))
owned = {}
errors, cleanup = [], []
proc = None
start = time.monotonic()
reason = None
peak_rss = peak_disk = 0
cpu = {}
handles = {}
last_progress = start
last_signature = None
result = {}


def observed():
    for pid, created in tuple(owned.items()):
        try:
            process = psutil.Process(pid)
            if process.create_time() != created:
                continue
            for child in process.children(recursive=True):
                owned[child.pid] = child.create_time()
        except psutil.NoSuchProcess:
            pass
        except psutil.Error as error:
            errors.append(dict(stage='discover', error=repr(error)))
    live = []
    for pid, created in tuple(owned.items()):
        try:
            process = psutil.Process(pid)
            if process.create_time() == created and process.is_running():
                live.append(process)
        except psutil.NoSuchProcess:
            pass
    return live


def storage(root):
    files = [p for p in root.rglob('*') if p.is_file()] if root.exists() else []
    sizes = []
    signature = []
    for path in files:
        try:
            stat = path.stat()
            sizes.append(stat.st_size)
            signature.append((str(path), stat.st_size, stat.st_mtime_ns))
        except FileNotFoundError:
            continue
    return sum(sizes), tuple(signature)


try:
    with (out/'stdout.txt').open('wb') as stdout, (out/'stderr.txt').open('wb') as stderr:
        env = dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
        proc = subprocess.Popen(command, cwd=REPO, env=env, stdout=stdout, stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        owned[proc.pid] = psutil.Process(proc.pid).create_time()
        while True:
            live = observed()
            rss = 0
            for process in live:
                try:
                    rss += process.memory_info().rss
                    values = process.cpu_times()
                    cpu[process.pid] = values.user+values.system
                    handles[process.pid] = max(handles.get(process.pid, 0), process.num_handles())
                except psutil.NoSuchProcess:
                    pass
            disk_base, signature = storage(base)
            disk = disk_base+storage(out)[0]
            peak_rss, peak_disk = max(peak_rss, rss), max(peak_disk, disk)
            now = time.monotonic()
            if signature != last_signature:
                last_progress, last_signature = now, signature
            row = dict(elapsed=now-start, tree_rss_bytes=rss, logical_bytes=disk,
                       live_pids=[p.pid for p in live], since_progress_seconds=now-last_progress)
            with (out/'monitor.jsonl').open('a', encoding='utf-8') as log:
                log.write(json.dumps(row)+'\n')
            print(json.dumps(dict(label=label, **row)), flush=True)
            if proc.poll() is not None:
                break
            reason = ('wall_limit' if now-start > seconds else 'rss_limit' if rss > rss_cap else
                      'storage_limit' if disk > disk_cap else 'no_progress' if now-last_progress > 120 else None)
            if reason:
                break
            time.sleep(5)
        if reason:
            for process in reversed(observed()):
                try:
                    process.kill()
                    cleanup.append(dict(pid=process.pid, action='kill_owned', reason=reason))
                except psutil.NoSuchProcess:
                    pass
            proc.wait(timeout=15)
        else:
            proc.wait()
        result['exit_code'] = proc.returncode
except BaseException:
    result['error'] = traceback.format_exc()
finally:
    remaining = observed()
    for process in reversed(remaining):
        try:
            process.kill()
            cleanup.append(dict(pid=process.pid, action='kill_owned_tail'))
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(remaining, timeout=5)
    remaining = observed()
    after = {name: sha256(Path(name).read_bytes()).hexdigest() for name in pins}
    result.update(reason=reason, outer_seconds=time.monotonic()-start, peak_sampled_tree_rss_bytes=peak_rss,
        peak_logical_bytes=peak_disk, observed_cpu_seconds=sum(cpu.values()), max_observed_handles=handles,
        source_unchanged=after == pins, observed_processes=owned,
        observed_processes_remaining=[p.pid for p in remaining], observed_processes_absent=not remaining,
        complete_process_tree_absence_proven=False, cleanup_events=cleanup, monitor_errors=errors,
        retained_root=str(base), all_artifacts_retained=True, formal_result=False)
    save('terminal.json', result)
    print(json.dumps(result), flush=True)
sys.exit(0 if result.get('exit_code') == 0 and not reason and not errors and not remaining
         and result['source_unchanged'] and 'error' not in result else 1)
