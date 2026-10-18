"""One bounded code-churn pair; no model, Job, solver or data imports."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
HELPER = REPO/'tests/h1_gil_stack_observer_development_v1.py'
POLICY = HERE.parent/'validation_path_optimization_01/entry_revision_04/interpreter_path_policy_v1.json'


def worker(mode, root):
    import gc
    sys.path[:] = json.loads(POLICY.read_bytes())['configured_paths']
    from tests.h1_gil_stack_observer_development_v1 import observe_owner_stack
    from contextlib import contextmanager

    @contextmanager
    def old_timer():
        import faulthandler
        faulthandler.enable()
        with (root/'stack.log').open('x') as stream:
            faulthandler.dump_traceback_later(.001, repeat=True, file=stream)
            try:
                yield None
            finally:
                faulthandler.cancel_dump_traceback_later()

    receipt = None
    context = old_timer() if mode == 'c_timer' else observe_owner_stack(
        root/'stack.jsonl', interval_seconds=.001, max_frames=32)
    iterations = 0
    source = ('def churn(depth):\n'
        ' if depth: return churn(depth-1)\n'
        ' return tuple(sum(x for x in range(i)) for i in range(12))\n')
    start = time.monotonic()
    with context as receipt:
        while time.monotonic()-start < 6.:
            namespace = {}
            exec(compile(source, '<transient-frame-churn>', 'exec'), namespace)
            assert namespace['churn'](12)[-1] == 55
            del namespace
            iterations += 1
            if iterations % 64 == 0:
                gc.collect()
                time.sleep(0)
    if receipt is not None:
        assert receipt['sampler_stopped'] and not receipt['errors'] and receipt['samples'] > 0
    result = dict(mode=mode, iterations=iterations, elapsed_seconds=time.monotonic()-start,
        observer_receipt=receipt, formal_result=False)
    with (root/'result.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)


if len(sys.argv) == 4 and sys.argv[1] == '--worker':
    worker(sys.argv[2], Path(sys.argv[3]))
    raise SystemExit(0)
if len(sys.argv) != 1:
    raise ValueError('fixed pair or internal worker role required')

import psutil

OUT = HERE/'stack_sampler_churn_pair_01'
OUT.mkdir(exist_ok=False)
pins = {str(path):sha256(path.read_bytes()).hexdigest() for path in (Path(__file__).resolve(), HELPER, POLICY)}
plan = dict(question='Can C timed dumps crash the same interpreter under frame churn, and does the Python sampler complete it?',
    workload='compile/execute/discard one recursive function, depth12; periodic GC; six seconds per mode',
    attempts_per_mode=1, modes=['c_timer', 'python_sampler'], timer_interval_seconds=.001,
    per_child_wall_cap_seconds=10, aggregate_sampled_rss_cap_bytes=256*1024**2,
    storage_cap_bytes=16*1024**2, worker_subprocesses_spawned=0,
    package_scope='Python standard library plus the diagnostic sampler; no project science modules',
    cleanup='Popen handle kill and bounded wait on cap; children cannot spawn processes by this fixed worker source',
    source_sha256=pins, formal_result=False, resource_admission=False,
    interpretation='A negative C-timer reproduction does not rule out a rare race; this pair alone does not establish full slice stability')
with (OUT/'plan.json').open('x', encoding='utf-8') as stream:
    json.dump(plan, stream, indent=2)
tested = OUT/'tested_bytes'
tested.mkdir()
for name in pins:
    path = Path(name)
    (tested/path.name).write_bytes(path.read_bytes())
results = {}
peak = 0
for mode in plan['modes']:
    root = OUT/mode
    root.mkdir()
    command = [sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--worker', mode, str(root)]
    stop = None
    start = time.monotonic()
    with (root/'stdout.log').open('x', encoding='utf-8') as log:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        process = psutil.Process(child.pid)
        creation = process.create_time()
        try:
            while child.poll() is None:
                elapsed = time.monotonic()-start
                try:
                    rss = process.memory_info().rss + psutil.Process().memory_info().rss
                except psutil.NoSuchProcess:
                    rss = 0
                peak = max(peak, rss)
                total = sum(path.stat().st_size for path in OUT.rglob('*') if path.is_file())
                if elapsed > 10 or rss > 256*1024**2 or total > 16*1024**2:
                    stop = 'wall' if elapsed > 10 else 'rss' if rss > 256*1024**2 else 'storage'
                    child.kill()
                    break
                time.sleep(.02)
        finally:
            if child.poll() is None:
                child.kill()
            code = child.wait(timeout=3)
    try:
        current = psutil.Process(child.pid)
        absent = current.create_time() != creation or not current.is_running()
    except psutil.NoSuchProcess:
        absent = True
    assert absent
    results[mode] = dict(command=command, pid=child.pid, creation_time=creation,
        exit_code=code, exit_code_hex=hex(code), stop_reason=stop,
        elapsed_seconds=time.monotonic()-start, recorded_direct_pid_absent=True,
        result=json.loads((root/'result.json').read_bytes()) if (root/'result.json').exists() else None)
    with (root/'terminal.json').open('x', encoding='utf-8') as stream:
        json.dump(results[mode], stream, indent=2)

assert all(sha256(Path(name).read_bytes()).hexdigest() == pin for name,pin in pins.items())
after = dict(results=results, peak_sampled_rss_including_monitor=peak,
    source_unchanged=True, c_timer_crash_reproduced=results['c_timer']['exit_code'] == 0xC0000005,
    python_sampler_completed=results['python_sampler']['exit_code'] == 0,
    full_slice_stability_verified=False, formal_result=False, resource_admission=False)
with (OUT/'comparison.json').open('x', encoding='utf-8') as stream:
    json.dump(after, stream, indent=2)
print(json.dumps(after), flush=True)
raise SystemExit(0 if after['python_sampler_completed'] and all(row['stop_reason'] is None for row in results.values()) else 1)
