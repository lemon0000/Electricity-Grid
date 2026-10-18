"""Cost ceiling for immutable-code byte reuse; not an integrated candidate."""
from contextlib import ExitStack
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from time import perf_counter
from types import ModuleType

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PACKAGE = HERE.parent/'validation_path_optimization_01/entry_revision_04'
assert len(sys.argv) == 3 and sys.argv[1] == '--basetemp'
out = Path(sys.argv[2])
assert out.is_absolute() and out.name.endswith('_non_authoritative')
out.mkdir(exist_ok=False)
manifest_raw = (PACKAGE/'package_manifest_v1.json').read_bytes()
assert sha256(manifest_raw).hexdigest() == 'd13a08fe6db35e9c5c70b8204e3fb4d0091e43a3ef483e3951a561eac0667e43'
manifest = json.loads(manifest_raw)['files_sha256']
assert all(sha256((PACKAGE/name).read_bytes()).hexdigest() == pin for name,pin in manifest.items())
sys.path[:] = json.loads((PACKAGE/'interpreter_path_policy_v1.json').read_bytes())['configured_paths']
from experiments import h1_guarded_ingress_development_v1 as guarded
ingress = guarded.ingress
reader, pins_function = ingress.read_stable, guarded.implementation_pins
reader_code, pins_code = reader.__code__, pins_function.__code__
paths = tuple(Path(name) for name in (guarded.__file__, guarded.guard.__file__,
    guarded.guard.grammar.__file__, guarded.guard.syntax.__file__, ingress.__file__,
    guarded.timing.__file__, guarded.timing.prior_timing.__file__))
expected = {path:sha256(path.read_bytes()).hexdigest() for path in paths}
code = (PACKAGE/'code_read_lease.py').read_bytes()
namespace = ModuleType('stable_read_cost_code_lease')
namespace.__file__ = str(PACKAGE/'code_read_lease.py')
exec(compile(code, namespace.__file__, 'exec'), namespace.__dict__)
plan = dict(question='Is avoiding repeated open/read of the seven immutable implementation-pin files worth implementing?',
    modes=['original_implementation_pins', 'shadow_fixed_cap_read_with_held_fd'],
    windows=['original', 'shadow', 'shadow', 'original'], iterations_per_window=128,
    exact_cap=1024**2, files=len(paths), code_read_lease_sha256=sha256(code).hexdigest(),
    files_sha256={str(path):pin for path,pin in expected.items()},
    shadow_scope='same two pathname stat and two fstat checks plus original digest per file; privately held fd under OS write/delete-denying code lease; no Path.open dispatch admission overhead',
    qualification='cost ceiling only; no original function, module binding or Path.open replacement; not a correctness or integration acceptance test',
    source_cache=False, numerical_cache=False, real_native_calls=0,
    formal_result=False, resource_admission=False)
with (out/'plan.json').open('x', encoding='utf-8') as stream:
    json.dump(plan, stream, indent=2)
measured = []
with ExitStack() as stack:
    lease = stack.enter_context(namespace.CodeReadLease(expected, root=REPO))
    streams = {path:stack.enter_context(path.open('rb')) for path in paths}
    raw_by_path = {path:reader(path, 1024**2)[0] for path in paths}

    def shadow_read(path):
        before = ingress.identity(path)
        if before[2] > 1024**2:
            raise ValueError('file byte cap exceeded')
        descriptor = streams[path].fileno()
        info = os.fstat(descriptor)
        opened = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        if opened[:4] != before[:4]:
            raise ValueError('file replaced before open')
        raw = raw_by_path[path]
        info = os.fstat(descriptor)
        after = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        if len(raw) > 1024**2 or len(raw) != before[2] or after != opened or ingress.identity(path) != before:
            raise ValueError('file changed or exceeded byte cap')
        return raw, before

    def shadow_pins():
        return {path.name:ingress.digest(shadow_read(path)[0]) for path in paths}

    for path in paths:
        assert shadow_read(path) == reader(path, 1024**2)
    baseline = pins_function()
    assert shadow_pins() == baseline
    for mode in plan['windows']:
        function = pins_function if mode == 'original' else shadow_pins
        start = perf_counter()
        for _ in range(128):
            result = function()
            assert result == baseline
        measured.append(dict(mode=mode, calls=128, wall_seconds=perf_counter()-start))
    lease_receipt = lease.receipt()
assert ingress.read_stable is reader and reader.__code__ is reader_code
assert guarded.implementation_pins is pins_function and pins_function.__code__ is pins_code
assert all(sha256(path.read_bytes()).hexdigest() == pin for path,pin in expected.items())
original = sum(row['wall_seconds'] for row in measured if row['mode'] == 'original')
shadow = sum(row['wall_seconds'] for row in measured if row['mode'] == 'shadow')
summary = dict(measurements=measured, original_seconds=original, shadow_seconds=shadow,
    shadow_reduction_fraction=(original-shadow)/original,
    original_functions_and_code_unchanged=True, raw_and_stamp_pairs_equal=True,
    all_implementation_pins_equal=True, source_unchanged=True, held_fd_count=len(streams),
    code_lease_receipt=lease_receipt, integrated_dispatch_overhead_measured=False,
    full_chain_speedup_measured=False, formal_result=False, resource_admission=False)
with (out/'comparison.json').open('x', encoding='utf-8') as stream:
    json.dump(summary, stream, indent=2)
print(json.dumps({key:value for key,value in summary.items() if key != 'code_lease_receipt'}), flush=True)
