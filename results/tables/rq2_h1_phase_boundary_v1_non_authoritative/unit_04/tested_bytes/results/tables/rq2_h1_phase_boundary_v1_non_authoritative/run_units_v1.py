"""One bounded, zero-Job phase/body unit invocation; retains all artifacts."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import psutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
label = sys.argv[1]
if not label.replace('_', '').isalnum():
    raise ValueError('fresh unit label required')
out = HERE / label
base = Path('D:/') / f'h1_phase_boundary_{label}_non_authoritative'
if out.exists() or base.exists():
    raise ValueError('unit roots must be fresh')
out.mkdir()
command = [sys.executable, '-u', '-B', '-m', 'pytest', '-q',
           '-p', 'no:cacheprovider', '-p', 'no:faulthandler',
           '--basetemp', str(base), '--junitxml', str(out / 'junit.xml'),
           'tests/test_h1_phase_boundary_budget_development_v1.py',
           'tests/test_h1_phase_boundary_due_endpoint_development_v1.py']
prior = REPO / 'results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03/request.json'
pins = json.loads(prior.read_bytes())['sources_sha256']
new = [Path(__file__), HERE / 'design_and_budget.md', HERE / 'budget_audit_v1.json',
       REPO / 'experiments/h1_phase_boundary_budget_development_v1.py',
       REPO / 'tests/test_h1_phase_boundary_budget_development_v1.py',
       REPO / 'tests/test_h1_phase_boundary_due_endpoint_development_v1.py']
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


save('request.json', dict(command=command, wall_cap_seconds=180,
    sampled_tree_rss_cap_bytes=1024 ** 3, logical_storage_cap_bytes=128 * 1024 ** 2,
    sample_seconds=2, base=str(base), sources_sha256=pins,
    reused_source_map_sha256=sha256(prior.read_bytes()).hexdigest(),
    source_map_reuse_does_not_rerun_prior_tests=True,
    permitted_child='direct Windows System32/conhost.exe console helper',
    launcher_probe='collection_probe_01/result.json',
    scope='detached_business_histories_and_original_phase_bodies',
    native_authorized=False, new_normal_jobs_authorized=False, formal_result=False))
started = time.monotonic()
owned = {}
observed_images = {}
peak_rss = peak_disk = 0
reason = None
cleanup = []
process = None
result = {}
next_heartbeat = 0
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
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file()) if root.exists() else 0


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
            rss = 0
            cpu = 0
            unexpected = []
            for item in live():
                try:
                    rss += item.memory_info().rss
                    times = item.cpu_times()
                    cpu += times.user + times.system
                    image = item.exe()
                    parent = item.ppid()
                    observed_images[str(item.pid)] = dict(executable=image, parent_pid=parent,
                        create_time=item.create_time(), command=item.cmdline())
                    if (item.pid != process.pid and
                            (os.path.normcase(image) != console_image or parent != process.pid)):
                        unexpected.append(item.pid)
                except psutil.NoSuchProcess:
                    pass
            disk = logical_bytes(out) + logical_bytes(base)
            elapsed = time.monotonic() - started
            peak_rss, peak_disk = max(peak_rss, rss), max(peak_disk, disk)
            row = dict(elapsed=elapsed, rss_bytes=rss, logical_bytes=disk, cpu_seconds=cpu)
            with (out / 'monitor.jsonl').open('a', encoding='utf-8') as monitor:
                monitor.write(json.dumps(row) + '\n')
            if elapsed >= next_heartbeat:
                print(json.dumps(row), flush=True)
                next_heartbeat = elapsed + 30
            reason = ('wall_limit' if elapsed > 180 else 'rss_limit' if rss > 1024 ** 3 else
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
        cases = ET.parse(out / 'junit.xml').getroot().findall('.//testcase')
        junit = dict(tests=len(cases), failures=sum(len(c.findall('failure')) for c in cases),
            errors=sum(len(c.findall('error')) for c in cases), skipped=sum(len(c.findall('skipped')) for c in cases))
        junit['accepted'] = junit == dict(tests=15, failures=0, errors=0, skipped=0)
        facts = {}
        for path in sorted(base.rglob('*fact.json')):
            raw = path.read_bytes()
            fact = json.loads(raw)
            if (fact.get('formal_result') is not False or fact.get('real_native_calls') != 0
                    or fact.get('phase_events_written') != 0
                    or fact.get('source_prefix_authenticated') is not False
                    or fact.get('paired_owner_authenticated') is not False):
                raise ValueError('fact scope differs from the detached unit contract')
            name = f"{fact.get('label', 'exact_due')}_{fact.get('business_hours', 192)}.json"
            target = out / 'facts' / name
            target.parent.mkdir(exist_ok=True)
            with target.open('xb') as stream:
                stream.write(raw)
            facts[str(path)] = dict(retained_copy=str(target), sha256=sha256(raw).hexdigest())
        result.update(junit=junit, facts=facts, expected_fact_count=9,
                      all_expected_facts_retained=len(facts) == 9)
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
    result.update(reason=reason, outer_seconds=time.monotonic() - started,
        peak_sampled_tree_rss_bytes=peak_rss, peak_logical_bytes=peak_disk,
        changed_sources=changed, source_pins=len(pins), observed_processes=owned,
        observed_images=observed_images,
        observed_processes_remaining=[p.pid for p in live()], cleanup_events=cleanup,
        complete_unobserved_process_tree_proof=False,
        new_normal_jobs=0, real_native_calls=0, formal_result=False)
    save('terminal.json', result)
    print(json.dumps(result), flush=True)
sys.exit(0 if result.get('exit_code') == 0 and reason is None
         and result.get('junit', {}).get('accepted') and result.get('all_expected_facts_retained')
         and not result.get('error') and not changed and not result['observed_processes_remaining'] else 1)
