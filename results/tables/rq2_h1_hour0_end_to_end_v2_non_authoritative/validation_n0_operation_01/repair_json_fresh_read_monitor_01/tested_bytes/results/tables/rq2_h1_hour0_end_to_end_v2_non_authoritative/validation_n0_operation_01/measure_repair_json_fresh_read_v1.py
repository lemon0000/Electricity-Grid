"""One small fresh-read comparison; no monkeypatch, cache, solver or live mutation."""
import ctypes
from ctypes import wintypes
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
OUT = HERE / 'repair_json_fresh_read_01_non_authoritative'
OUT.mkdir(exist_ok=False)
PINS = {
    REPO / 'results/tables/rq2_h1_outage_registry_v1_non_authoritative/scientific_development_authority.json':
        '45710f18fcf98113d53c50cd74e0dfc311ad3e03cfb8ab8f75b01dc2720de0a8',
    REPO / 'results/tables/rq2_h1_outage_origin_replay_v1_non_authoritative/repair_cap_proposal.json':
        '6435c85b6cc99d243077bd014b1f52cc90427270a4c50cb26a67fb7e34edf031',
}
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
    wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
kernel.CreateFileW.restype = wintypes.HANDLE
kernel.ReadFile.argtypes = (wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID)
kernel.ReadFile.restype = wintypes.BOOL
kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel.CloseHandle.restype = wintypes.BOOL

def path_read(path):
    return path.read_bytes()

def io_read(path):
    with io.open(path, 'rb') as stream:
        return stream.read()

def fd_read(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_BINARY)
    try:
        parts = []
        while block := os.read(descriptor, 32768):
            parts.append(block)
        return b''.join(parts)
    finally:
        os.close(descriptor)

def win32_read(path):
    handle = kernel.CreateFileW(str(path), 0x80000000, 3, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        parts = []
        while True:
            buffer = ctypes.create_string_buffer(32768)
            count = wintypes.DWORD()
            if not kernel.ReadFile(handle, buffer, len(buffer), ctypes.byref(count), None):
                raise ctypes.WinError(ctypes.get_last_error())
            if not count.value:
                return b''.join(parts)
            parts.append(buffer.raw[:count.value])
    finally:
        if not kernel.CloseHandle(handle):
            raise ctypes.WinError(ctypes.get_last_error())

started = time.perf_counter()
rows = []
for repeat in range(6):
    for path, pin in PINS.items():
        for method in (path_read, io_read, fd_read, win32_read):
            before = time.perf_counter()
            data = method(path)
            elapsed = time.perf_counter() - before
            if sha256(data).hexdigest() != pin:
                raise ValueError('fresh JSON pin differs')
            rows.append(dict(repeat=repeat, path=str(path), method=method.__name__,
                seconds=elapsed, bytes=len(data), sha256=pin))
result = dict(rows=rows, elapsed_seconds=time.perf_counter()-started, input_bytes_cached=False,
    each_read_opens_reads_and_closes=True, mutated_inputs=False, production_route_installed=False,
    source_sha256={str(Path(__file__)): sha256(Path(__file__).read_bytes()).hexdigest()},
    formal_result=False, resource_admission=False, full_hour0_chain_passed=False, exit_code=0)
with (OUT/'terminal.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(dict(elapsed_seconds=result['elapsed_seconds'], methods={
    method.__name__: sum(r['seconds'] for r in rows if r['method']==method.__name__)
    for method in (path_read, io_read, fd_read, win32_read)})))
