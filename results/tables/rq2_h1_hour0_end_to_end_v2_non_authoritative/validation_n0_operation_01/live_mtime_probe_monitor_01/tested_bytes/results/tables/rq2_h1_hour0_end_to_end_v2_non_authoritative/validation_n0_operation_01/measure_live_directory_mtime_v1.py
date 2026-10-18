"""Read-only feasibility probe, not an admitted metadata validation route."""
from collections import Counter
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


save('request.json', dict(question='Can fresh directory-handle mtime queries materially reduce stock path-stat cost with bit-exact successful values?',
    attempts=1, roots=roots, rounds_per_root=128,
    order='stock_before, live_handle_or_stock_fallback, stock_after',
    root_mutations=0, solver_calls=0, source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
    config_sha256=sha256(config_raw).hexdigest(), limits=dict(wall_seconds=30, sampled_rss_mib=256, storage_mib=16),
    acceptance='same stock bookends imply identical float.hex or None; close all observed handles',
    boundary='successful-value feasibility only; ACL/path-error equivalence not proven; no hook installed',
    formal_result=False, resource_admission=False))


class Basic(ctypes.Structure):
    _fields_ = [(name, ctypes.c_longlong) for name in ('creation', 'access', 'write', 'change')] + [('attributes', wintypes.DWORD)]


kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
    wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
kernel.CreateFileW.restype = wintypes.HANDLE
kernel.GetFileInformationByHandleEx.argtypes = (wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD)
kernel.GetFileInformationByHandleEx.restype = wintypes.BOOL
kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel.CloseHandle.restype = wintypes.BOOL
handles = []
rows = []
cleanup_errors = []
result = dict(exit_code=1, formal_result=False, resource_admission=False, admitted_route=False, solver_calls=0)
start = perf_counter_ns()


def stock(root):
    try:
        return os.stat(root).st_mtime
    except OSError:
        return None


try:
    for root in roots:
        path = Path(root)
        handle = None
        if path.is_dir() and path.resolve() == path and not path.stat().st_file_attributes & 0x400:
            # Shared read/write/delete here: this probe must not constrain the
            # configured roots and makes no namespace-stability claim.
            handle = kernel.CreateFileW(root, 0x80, 7, None, 3, 0x02200000, None)
            if handle == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            handles.append(handle)
        before_times, native_times, after_times = [], [], []
        stable = drift = 0
        outcomes = Counter()
        for ordinal in range(128):
            tick = perf_counter_ns()
            before = stock(root)
            before_times.append(perf_counter_ns() - tick)
            tick = perf_counter_ns()
            if handle is None:
                observed = stock(root)
            else:
                info = Basic()
                if not kernel.GetFileInformationByHandleEx(handle, 0, ctypes.byref(info), ctypes.sizeof(info)):
                    raise ctypes.WinError(ctypes.get_last_error())
                seconds = info.write // 10_000_000 - 11_644_473_600
                nanoseconds = (info.write % 10_000_000) * 100
                observed = seconds + 1e-9 * nanoseconds
            native_times.append(perf_counter_ns() - tick)
            tick = perf_counter_ns()
            after = stock(root)
            after_times.append(perf_counter_ns() - tick)
            if before == after:
                assert (None if observed is None else observed.hex()) == (None if before is None else before.hex())
                stable += 1
            else:
                drift += 1
            outcomes['none' if observed is None else 'mtime'] += 1
        rows.append(dict(root=root, route='held_directory_query' if handle is not None else 'stock_fallback',
            stable_bookends=stable, changed_bookends=drift, outcomes=dict(outcomes),
            stock_mean_ns=statistics.mean(before_times + after_times),
            route_mean_ns=statistics.mean(native_times),
            stock_median_ns=statistics.median(before_times + after_times),
            route_median_ns=statistics.median(native_times)))
    result.update(exit_code=0, rows=rows, observed_handles=len(handles),
        successful_values_bit_exact=True, total_queries=len(roots)*128*3)
except BaseException as error:
    result.update(error=repr(error))
finally:
    elapsed = perf_counter_ns() - start
    closing = perf_counter_ns()
    for handle in reversed(handles):
        if not kernel.CloseHandle(handle):
            cleanup_errors.append(repr(ctypes.WinError(ctypes.get_last_error())))
    result.update(measured_and_acquisition_seconds=elapsed/1e9,
        cleanup_seconds=(perf_counter_ns()-closing)/1e9, cleanup_errors=cleanup_errors,
        all_observed_handles_closed=not cleanup_errors,
        config_unchanged=sha256(config.read_bytes()).hexdigest()==sha256(config_raw).hexdigest())
    if cleanup_errors or not result['config_unchanged']:
        result['exit_code'] = 1
    save('terminal.json', result)
    print(json.dumps(result), flush=True)
sys.exit(result['exit_code'])
