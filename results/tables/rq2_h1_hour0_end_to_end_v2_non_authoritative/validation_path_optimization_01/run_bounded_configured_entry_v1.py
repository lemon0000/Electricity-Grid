"""Observed limits for local development checks; no formal resource authority."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

import psutil


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
label, seconds, ram_mib, storage_mib, *arguments = sys.argv[1:]
if not label.replace('_', '').isalnum() or not arguments or arguments.pop(0) != '--':
    raise ValueError('unique label, limits and explicit command arguments required')
limit, ram, storage_cap = float(seconds), int(ram_mib) * 1024**2, int(storage_mib) * 1024**2
if not 0 < limit <= 600 or not 0 < ram <= 1024**3 or not 0 < storage_cap <= 128 * 1024**2:
    raise ValueError('bounded development limits exceeded')
out = HERE / label
out.mkdir(exist_ok=False)
command = [sys.executable, '-B', *arguments]
if len(arguments)<5 or arguments[0]!='-I':
    raise ValueError('explicit configured-entry invocation required')
launcher=(REPO/arguments[1]).resolve(strict=True)
entry=(HERE/'entry_revision_03').resolve(strict=True)
if launcher!=entry/'launch_validation.py' or not arguments[4].replace('_','').isalnum():
    raise ValueError('fixed entry and unique child attempt label required')
child_output=entry/arguments[4]
if child_output.exists():raise ValueError('fresh child attempt root required')
storage_roots=[out,child_output]



def save(name, value):
    with (out / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)


sources = {Path(__file__).resolve(), REPO / 'experiments/h1_canonical_path_lease_development_v1.py',
    REPO / 'tests/test_h1_canonical_path_lease_development_v1.py'}
sources.update(p for p in entry.iterdir() if p.is_file())
source_pins = {str(p): sha256(p.read_bytes()).hexdigest() for p in sources}
for path in sources:
    destination = out / 'tested_bytes' / path.relative_to(REPO)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(path.read_bytes())
save('request.json', dict(command=command, seconds=limit, sampled_rss_cap_bytes=ram,
    storage_cap_bytes=storage_cap, storage_roots=list(map(str, storage_roots)),
    source_sha256=source_pins,
    runner_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
    formal_result=False, resource_admission=False))
start = time.monotonic()
peak = storage = 0
reason = None
proc = target = None
result = {}
try:
    with (out / 'stdout.log').open('x', encoding='utf-8') as stream:
        proc = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)
        target = psutil.Process(proc.pid)
        save('started.json', dict(pid=proc.pid, creation_time=target.create_time()))
        next_storage = 0
        while proc.poll() is None:
            elapsed = time.monotonic() - start
            try:
                processes = [target, *target.children(recursive=True)]
                rss = sum(p.memory_info().rss for p in processes if p.is_running())
                peak = max(peak, rss)
            except psutil.Error:
                rss = 0
            if elapsed >= next_storage:
                storage = sum(p.stat().st_size for root in storage_roots if root.exists()
                    for p in root.rglob('*') if p.is_file())
                next_storage = elapsed + 1
            if elapsed > limit or rss > ram or storage > storage_cap:
                reason = 'wall' if elapsed > limit else 'rss' if rss > ram else 'storage'
                for child in reversed(target.children(recursive=True)):
                    try:
                        child.kill()
                    except psutil.Error:
                        pass
                proc.kill()
                break
            time.sleep(0.1)
        result['exit_code'] = proc.wait()
except BaseException:
    result.update(exit_code=None, error=traceback.format_exc())
    if proc is not None and proc.poll() is None:
        if target is not None:
            for child in reversed(target.children(recursive=True)):
                try: child.kill()
                except psutil.Error: pass
        proc.kill()
        proc.wait()
finally:
    drift = [name for name, pin in source_pins.items()
        if not Path(name).is_file() or sha256(Path(name).read_bytes()).hexdigest() != pin]
    if drift:
        result.update(exit_code=1, source_drift=drift)
    result.update(elapsed_seconds=time.monotonic() - start, stop_reason=reason,
        peak_observed_process_tree_rss=peak, observed_storage_bytes=storage,
        memory_is_sampled=True, source_unchanged=not drift,
        formal_result=False, resource_admission=False)
    save('terminal.json', result)
    print(json.dumps(result), flush=True)
sys.exit(0 if result.get('exit_code') == 0 and reason is None else 1)
