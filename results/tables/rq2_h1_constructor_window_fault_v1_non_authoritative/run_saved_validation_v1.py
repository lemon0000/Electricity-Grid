"""One pre-budgeted H3 reconstruction or H1 fixed-order comparison invocation."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PRIOR = HERE.parent / 'rq2_h1_constructor_inspection_v2_non_authoritative'
mode, label = sys.argv[1:]
options = {
    'oracle': ('oracle_saved_v2.py', 'oracle_terminal.json', 1,
               'one_saved_H3_M5_new_batch_identity_bound_science_reconstruction'),
    'short': ('compare_short_saved_v2.py', 'comparison_terminal.json', 2,
              'two_saved_H1_M5_batches_fixed_old_then_new_net_cost'),
}
worker, terminal_name, batches, scope = options[mode]
if not label.replace('_', '').isalnum():
    raise ValueError('fresh diagnostic label required')
out = HERE / label
if out.exists():
    raise ValueError('diagnostic output must be fresh')
out.mkdir()
command = [sys.executable, '-u', '-B', str(HERE / worker), str(out)]
prior = REPO / 'results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03/request.json'
pins = json.loads(prior.read_bytes())['sources_sha256']
if any(sha256(Path(name).read_bytes()).hexdigest() != expected for name, expected in pins.items()):
    raise ValueError('inherited source bytes differ before diagnostic launch')
new = [Path(__file__), HERE / 'design_and_budget.md', HERE / worker,
       PRIOR / 'oracle_saved_v1.py', PRIOR / 'compare_saved_v1.py',
       HERE.parent / 'rq2_h1_source_replay_cost_v1_non_authoritative/profile_saved_v1.py',
       REPO / 'tests/h1_cross_hour_identity_fixture_v1.py',
       REPO / 'experiments/h1_constructor_inspection_capture_development_v1.py',
       REPO / 'experiments/h1_phase_historical_batch_development_v2.py',
       REPO / 'experiments/h1_phase_exact_source_batch_development_v2.py',
       REPO / 'experiments/h1_constructor_source_batch_validation_development_v1.py']
if mode == 'short':
    new += [HERE / 'oracle_01/oracle_terminal.json', HERE / 'oracle_01/terminal.json']
for path in new:
    raw = path.read_bytes()
    pins[str(path)] = sha256(raw).hexdigest()
    target = out / 'tested_bytes' / path.relative_to(REPO)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)


def save(name, value):
    with (out / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


save('request.json', dict(command=command, wall_cap_seconds=240,
    no_source_read_activity_cap_seconds=90, full_batches=batches,
    sampled_tree_rss_cap_bytes=1024 ** 3, logical_storage_cap_bytes=128 * 1024 ** 2,
    sample_seconds=2, sources_sha256=pins,
    reused_source_map_sha256=sha256(prior.read_bytes()).hexdigest(),
    source_map_reuse_does_not_rerun_prior_tests=True,
    permitted_child='direct Windows System32/conhost.exe console helper',
    scope=scope, static_identity_memo=False, shared_saved_manifest_pin_resolver=True,
    native_authorized=False, new_normal_jobs_authorized=False, formal_result=False))
started = time.monotonic()
owned, observed_images, cleanup = {}, {}, []
peak_rss = peak_disk = 0
reason = None
process = None
result = {}
next_heartbeat = 0
last_activity, activity_stamp = started, 0
console_image = os.path.normcase(str(Path(os.environ['SystemRoot']) / 'System32/conhost.exe'))


def live():
    found = []
    for pid, created in tuple(owned.items()):
        try:
            item = psutil.Process(pid)
            if item.create_time() == created and item.is_running():
                found.append(item)
        except psutil.NoSuchProcess:
            pass
    return found


def logical_bytes(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())


try:
    with (out / 'stdout.txt').open('wb') as stdout, (out / 'stderr.txt').open('wb') as stderr:
        process = subprocess.Popen(command, cwd=REPO, stdout=stdout, stderr=stderr,
            env=dict(os.environ, PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1'),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        owned[process.pid] = psutil.Process(process.pid).create_time()
        while True:
            for item in live():
                for child in item.children(recursive=True):
                    owned[child.pid] = child.create_time()
            rss = cpu = 0
            unexpected = []
            for item in live():
                try:
                    rss += item.memory_info().rss
                    times = item.cpu_times()
                    cpu += times.user + times.system
                    executable, parent = item.exe(), item.ppid()
                    observed_images[str(item.pid)] = dict(executable=executable,
                        parent_pid=parent, create_time=item.create_time(), command=item.cmdline())
                    if item.pid != process.pid and (os.path.normcase(executable) != console_image or parent != process.pid):
                        unexpected.append(item.pid)
                except psutil.NoSuchProcess:
                    pass
            disk = logical_bytes(out)
            now = time.monotonic()
            elapsed = now - started
            peak_rss, peak_disk = max(peak_rss, rss), max(peak_disk, disk)
            activity = out / 'source_read_activity.json'
            stamp = activity.stat().st_mtime_ns if activity.exists() else 0
            if stamp != activity_stamp:
                activity_stamp, last_activity = stamp, now
            row = dict(elapsed_seconds=elapsed, no_source_read_activity_seconds=now-last_activity,
                rss_bytes=rss, logical_bytes=disk, cpu_seconds=cpu)
            with (out / 'monitor.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(row)+'\n')
            if elapsed >= next_heartbeat:
                print(json.dumps(row), flush=True)
                next_heartbeat = elapsed + 30
            reason = ('wall_limit' if elapsed > 240 else
                      'no_source_read_activity_limit' if now-last_activity > 90 else
                      'rss_limit' if rss > 1024 ** 3 else
                      'storage_limit' if disk > 128 * 1024 ** 2 else
                      'unexpected_child_process' if unexpected else None)
            if reason or process.poll() is not None:
                break
            time.sleep(2)
        if reason:
            for item in reversed(live()):
                item.kill()
                cleanup.append(dict(pid=item.pid, action='kill_owned', reason=reason))
        process.wait(timeout=10)
        result['exit_code'] = process.returncode
        terminal = json.loads((out / terminal_name).read_bytes())
        result.update(worker_terminal=terminal_name, worker=terminal,
                      worker_accepted=terminal['exit_code'] == 0)
except BaseException as error:
    result['error'] = repr(error)
finally:
    for item in reversed(live()):
        try:
            item.kill()
            cleanup.append(dict(pid=item.pid, action='kill_owned_tail'))
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(live(), timeout=5)
    changed = [name for name, expected in pins.items()
               if sha256(Path(name).read_bytes()).hexdigest() != expected]
    result.update(reason=reason, outer_seconds=time.monotonic()-started,
        peak_sampled_tree_rss_bytes=peak_rss, peak_logical_bytes=peak_disk,
        changed_sources=changed, source_pins=len(pins), observed_processes=owned,
        observed_images=observed_images, observed_processes_remaining=[p.pid for p in live()],
        cleanup_events=cleanup, complete_unobserved_process_tree_proof=False,
        new_normal_jobs=0, real_native_calls=0, formal_result=False)
    save('terminal.json', result)
    print(json.dumps(dict(exit_code=result.get('exit_code'), worker_accepted=result.get('worker_accepted'),
        reason=reason, error=result.get('error'), outer_seconds=result['outer_seconds'],
        peak_sampled_tree_rss_bytes=peak_rss, peak_logical_bytes=peak_disk,
        changed_sources=changed, source_pins=len(pins), remaining=result['observed_processes_remaining'])), flush=True)
sys.exit(0 if result.get('exit_code') == 0 and reason is None and result.get('worker_accepted')
         and not result.get('error') and not changed and not result['observed_processes_remaining'] else 1)
