"""Fresh path-query feasibility only; no metadata hook or project/solver import."""
import ctypes
from ctypes import wintypes
from hashlib import sha256
import json
import os
from pathlib import Path
import statistics
import sys
from time import perf_counter_ns

flag, location = sys.argv[1:]
assert flag == '--basetemp' and sys.flags.isolated and sys.dont_write_bytecode
OUT = Path(location)
assert OUT.is_absolute() and OUT.name.endswith('_non_authoritative')
OUT.mkdir(exist_ok=False)
HERE = Path(__file__).resolve().parent
config = HERE.parent / 'validation_path_optimization_01/entry_revision_07/interpreter_path_policy_v1.json'
config_raw = config.read_bytes()
assert sha256(config_raw).hexdigest() == '1fc8f15125d826e5631d6c8f7504b59eac1d0e0a337a13c0ae956c5bcd9e4531'
roots = json.loads(config_raw)['configured_paths']
assert len(roots) == 8


def save(name, value):
    with (OUT / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)


class StatBasic(ctypes.Structure):
    # Only consume these two documented fields; preserve the full ABI size.
    _fields_ = [(name, ctypes.c_longlong) for name in (
        'FileId', 'CreationTime', 'LastAccessTime', 'LastWriteTime', 'ChangeTime', 'AllocationSize', 'EndOfFile')]
    _fields_ += [('FileAttributes', wintypes.DWORD), ('remaining', ctypes.c_ubyte * 44)]


assert ctypes.sizeof(StatBasic) == 104 and ctypes.alignment(StatBasic) == 8
assert StatBasic.LastWriteTime.offset == 24 and StatBasic.FileAttributes.offset == 56
kernel = ctypes.WinDLL('api-ms-win-core-file-l2-1-4', use_last_error=True)
query = kernel.GetFileInformationByName
query.argtypes = (wintypes.LPCWSTR, ctypes.c_int, wintypes.LPVOID, wintypes.ULONG)
query.restype = wintypes.BOOL
eligible = {name for name in roots if Path(name).is_dir() and not Path(name).stat().st_file_attributes & 0x400}
save('request.json', dict(question='Is the same fresh named stat fast path materially cheaper when only mtime is converted?',
    attempts=1, roots=roots, rounds_per_root=128, root_mutations=0, solver_calls=0,
    api='api-ms-win-core-file-l2-1-4.GetFileInformationByName', info_class=3,
    abi=dict(size=104, alignment=8, last_write_offset=24, attributes_offset=56),
    source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
    config_sha256=sha256(config_raw).hexdigest(), limits=dict(wall_seconds=30, sampled_rss_mib=256, storage_mib=16),
    order='stock_before, named_query_or_stock_fallback, stock_after',
    acceptance='stable stock bookends require float.hex and integer ns equality; unknown/error/reparse/file routes stay stock',
    production_hook_installed=False, formal_result=False, resource_admission=False))


def stock(root):
    try:
        info = os.stat(root)
        return info.st_mtime, info.st_mtime_ns
    except OSError:
        return None, None


rows = []
result = dict(exit_code=1, formal_result=False, resource_admission=False,
    admitted_route=False, production_hook_installed=False, solver_calls=0)
start = perf_counter_ns()
try:
    for root in roots:
        stock_times, direct_times = [], []
        reasons = {}
        stable = changed = 0
        for _ in range(128):
            tick = perf_counter_ns()
            before = stock(root)
            stock_times.append(perf_counter_ns() - tick)
            tick = perf_counter_ns()
            info = StatBasic()
            if root not in eligible:
                reason = 'not_admitted_directory'
            elif not query(root, 3, ctypes.byref(info), ctypes.sizeof(info)):
                reason = 'api_error_' + str(ctypes.get_last_error())
            elif info.FileAttributes & 0x400 or not info.FileAttributes & 0x10:
                reason = 'reparse_or_not_directory'
            else:
                reason = 'named_query'
            if reason == 'named_query':
                seconds = info.LastWriteTime // 10_000_000 - 11_644_473_600
                nanoseconds = (info.LastWriteTime % 10_000_000) * 100
                observed = seconds + 1e-9 * nanoseconds, seconds * 1_000_000_000 + nanoseconds
            else:
                observed = stock(root)
            direct_times.append(perf_counter_ns() - tick)
            reasons[reason] = reasons.get(reason, 0) + 1
            tick = perf_counter_ns()
            after = stock(root)
            stock_times.append(perf_counter_ns() - tick)
            if before == after:
                assert observed[1] == before[1]
                assert (None if observed[0] is None else observed[0].hex()) == (None if before[0] is None else before[0].hex())
                stable += 1
            else:
                changed += 1
        rows.append(dict(root=root, stable_bookends=stable, changed_bookends=changed, route_counts=reasons,
            stock_mean_ns=statistics.mean(stock_times), direct_mean_ns=statistics.mean(direct_times),
            stock_median_ns=statistics.median(stock_times), direct_median_ns=statistics.median(direct_times),
            stock_p95_ns=sorted(stock_times)[int(.95*(len(stock_times)-1))],
            direct_p95_ns=sorted(direct_times)[int(.95*(len(direct_times)-1))]))
    result.update(exit_code=0, rows=rows, successful_values_bit_exact=True,
        integer_ns_equal=True, total_query_groups=len(roots)*128, retained_handles=0)
except BaseException as error:
    result.update(error=repr(error))
finally:
    result.update(elapsed_seconds=(perf_counter_ns()-start)/1e9,
        config_unchanged=sha256(config.read_bytes()).hexdigest()==sha256(config_raw).hexdigest())
    if not result['config_unchanged']:
        result['exit_code'] = 1
    save('terminal.json', result)
    print(json.dumps(result), flush=True)
sys.exit(result['exit_code'])
