"""Preserve the failed diagnostic and check its exact inputs and owned roots."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import msvcrt
import os
from pathlib import Path
import struct

import psutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PATH = HERE.parent / 'validation_path_optimization_01'
OUTER = PATH / 'configured_entry_05_common_slice_monitor_01'
INNER = PATH / 'entry_revision_05/common_slice_01'
SHORT = Path('D:/h1_cs01_non_authoritative')
OUT = HERE / 'common_slice_crash_01'
OUT.mkdir(exist_ok=False)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def absent(row):
    try:
        process = psutil.Process(row['pid'])
        return process.create_time() != row['creation_time'] or not process.is_running()
    except psutil.NoSuchProcess:
        return True


request = read(OUTER / 'request.json')
terminal = read(OUTER / 'terminal.json')
assert terminal['exit_code'] == 0xC0000005 and terminal['stop_reason'] is None
assert terminal['source_unchanged'] and terminal['source_snapshot_complete']
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']
assert terminal['final_storage_observation_complete'] and not terminal['storage_read_errors']
pins = request['source_sha256']
assert all(digest(Path(name)) == pin for name, pin in pins.items())
assert all(digest(OUTER / 'tested_bytes' / Path(name).relative_to(REPO)) == pin
           for name, pin in pins.items())
assert all(absent(row) for row in terminal['observed_owned_processes'])

before = {str(p): digest(p) for p in SHORT.rglob('*') if p.is_file()}
locks = sorted(p for p in SHORT.rglob('*') if p.is_file() and p.name.endswith('.lock'))
checked = []
for path in locks:
    assert path.stat().st_size > 0, path
    with path.open('r+b') as stream:
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            checked.append(str(path))
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
assert before == {str(p): digest(p) for p in SHORT.rglob('*') if p.is_file()}

timing = [json.loads(line) for line in (INNER / 'timing.jsonl').read_text().splitlines()]
assert [row['label'] for row in timing] == ['source_and_fixture_setup', 'slice_arm_0_open']
for source, target in ((INNER / 'pytest.log', 'pytest.log'),
                       (INNER / 'timing.jsonl', 'timing.jsonl'),
                       (SHORT / 'stack_samples.log', 'stack_samples.log')):
    (OUT / target).write_bytes(source.read_bytes())
assert not (INNER / 'terminal.json').exists()
assert not list(SHORT.rglob('guarded_common_slice_report.json'))

chain = HERE.parent / 'chain_07'
old_pins = read(chain / 'request.json')['before']
assert all(digest(Path(name)) == pin for name, pin in old_pins.items())
old_processes = []
for pid in (43640, 27888, 42184):
    try:
        process = psutil.Process(pid)
        old_processes.append(dict(pid=pid, creation_time=process.create_time(),
            command=process.cmdline(), status=process.status(), cpu_seconds=sum(process.cpu_times()[:2])))
    except psutil.NoSuchProcess:
        old_processes.append(dict(pid=pid, present=False))

# Read PE export and x64 unwind tables without loading or calling the DLL.
dll = Path('D:/Miniconda3/envs/compute/python312.dll')
raw = dll.read_bytes()
pe = struct.unpack_from('<I', raw, 0x3C)[0]
count = struct.unpack_from('<H', raw, pe + 6)[0]
optional = pe + 24
optional_size = struct.unpack_from('<H', raw, pe + 20)[0]
sections = []
for index in range(count):
    at = optional + optional_size + index * 40
    size, start, disk_size, disk_start = struct.unpack_from('<IIII', raw, at + 8)
    sections.append((start, max(size, disk_size), disk_start))


def offset(rva):
    for start, size, disk_start in sections:
        if start <= rva < start + size:
            return disk_start + rva - start
    raise ValueError('RVA is outside PE sections')


export_rva = struct.unpack_from('<I', raw, optional + 112)[0]
fields = struct.unpack_from('<IIHHIIIIIII', raw, offset(export_rva))
_, _, _, _, _, _, _, names_count, functions, names, ordinals = fields
fault = 0x2FBFE7
neighbors = []
for index in range(names_count):
    name_rva = struct.unpack_from('<I', raw, offset(names) + 4 * index)[0]
    at = offset(name_rva)
    name = raw[at:raw.index(b'\0', at)].decode('ascii')
    ordinal = struct.unpack_from('<H', raw, offset(ordinals) + 2 * index)[0]
    address = struct.unpack_from('<I', raw, offset(functions) + 4 * ordinal)[0]
    if abs(address - fault) < 0x1000:
        neighbors.append(dict(name=name, rva=hex(address), fault_minus_export=fault-address))
unwind_rva, unwind_size = struct.unpack_from('<II', raw, optional + 112 + 3 * 8)
unwind = []
for at in range(offset(unwind_rva), offset(unwind_rva) + unwind_size, 12):
    start, end, data = struct.unpack_from('<III', raw, at)
    if start <= fault < end:
        unwind.append(dict(start_rva=hex(start), end_rva=hex(end), unwind_rva=hex(data)))

report = Path('C:/ProgramData/Microsoft/Windows/WER/ReportArchive/'
    'AppCrash_python.exe_1d1d708b76ba5067eafc81eae2ca596670abad_19c43b13_c95558d9-1dc4-4885-bf27-e2dc0b2bc5a0/Report.wer')
wer_raw = report.read_bytes()
wer = wer_raw.decode('utf-16') if wer_raw.startswith((b'\xff\xfe', b'\xfe\xff')) else wer_raw.decode('utf-8-sig')
wer_rows = dict(line.split('=', 1) for line in wer.splitlines() if '=' in line)
selected = {key: wer_rows[key] for key in ('EventType', 'EventTime', 'IsFatal',
    'Sig[0].Value', 'Sig[1].Value', 'Sig[3].Value', 'Sig[4].Value', 'Sig[6].Value', 'Sig[7].Value')}

result = dict(status='FAILED_NATIVE_ACCESS_VIOLATION',
    observed_utc=datetime.now(timezone.utc).isoformat(),
    wrapper_tool_exit_code=1, child_exit_code=terminal['exit_code'],
    child_exit_code_hex=hex(terminal['exit_code']),
    resource_stop_reason=None, outer_terminal=terminal,
    completed_stage_timings=timing,
    uncompleted_stage='first N0 bootstrap; no slice_arm_0_N0 timing row',
    stages_not_reached=['second and third N0', 'CommonOwnerGenesis', 'live Rref',
        'two successor common calls', 'Actual', 'paired commit', 'close/reopen replay'],
    source_files_unchanged=len(pins), tested_source_copies_match=True,
    observed_owned_processes_absent=True, complete_process_tree_absence_proven=False,
    short_root_files_unchanged_by_postcheck=len(before),
    lock_paths_reacquired_and_released=checked,
    inner_terminal_present=False, slice_success_report_present=False,
    old_chain_inputs_unchanged=len(old_pins), old_chain_process_observation=old_processes,
    old_chain_terminal_present=(chain / 'terminal.json').exists(),
    native_fault_evidence=dict(windows_wer_selected_fields=selected,
        windows_wer_sha256=sha256(wer_raw).hexdigest(), python_dll_sha256=digest(dll),
        fault_rva=hex(fault), nearest_exports=sorted(neighbors, key=lambda row:int(row['rva'],16)),
        containing_unwind_ranges=unwind,
        inference='RVA lies between dump helpers; truncated fourth timed stack suggests asynchronous faulthandler dump race; exact native cause not proven without symbols or dump'),
    unchanged_retry_authorized=False, longer_budget_justified=False,
    full_hour0_chain_passed=False, full_192_hour_verified=False,
    official_review_verdict=None, formal_execution_ready=False, formal_result=False,
    resource_admission=False, native_execution_authorized=False,
    files_sha256={str(p.relative_to(REPO)):digest(p) for p in (
        Path(__file__), OUTER / 'request.json', OUTER / 'terminal.json',
        OUT / 'pytest.log', OUT / 'timing.jsonl', OUT / 'stack_samples.log')})
with (OUT / 'postcheck.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(dict(output=str(OUT / 'postcheck.json'), source_files=len(pins),
    locks=len(checked), old_chain_pins=len(old_pins), child_exit_hex=hex(terminal['exit_code']),
    unwind=unwind, elapsed_seconds=terminal['elapsed_seconds'])), flush=True)
