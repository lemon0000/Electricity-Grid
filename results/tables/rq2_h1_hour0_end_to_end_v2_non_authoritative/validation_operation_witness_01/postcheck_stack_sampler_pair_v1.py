"""Bind the existing short pair and its native event; do not rerun it."""
from hashlib import sha256
import json
from pathlib import Path

import psutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
OUT = HERE/'stack_sampler_churn_pair_01'


def read(path): return json.loads(path.read_bytes())
def digest(path): return sha256(path.read_bytes()).hexdigest()


comparison = read(OUT/'comparison.json')
plan = read(OUT/'plan.json')
event, = read(OUT/'windows_crash_event.json')
c = comparison['results']['c_timer']
python = comparison['results']['python_sampler']
assert c['exit_code'] == 0xC0000005 and python['exit_code'] == 0
assert c['stop_reason'] is python['stop_reason'] is None
assert event['id'] == 1000
assert int(event['event_data']['ProcessId'], 16) == c['pid']
assert event['event_data']['ExceptionCode'] == 'c0000005'
rva = int(event['event_data']['FaultingOffset'], 16)
assert 0x2FBFC0 <= rva < 0x2FC4D5
assert (OUT/'c_timer/stack.log').read_bytes().endswith(b'\n  File ')
for row in (c, python):
    try:
        current = psutil.Process(row['pid'])
        assert current.create_time() != row['creation_time'] or not current.is_running()
    except psutil.NoSuchProcess:
        pass
    assert read(OUT/row['result']['mode']/'result.json') == row['result'] if row['result'] else True

for name,pin in plan['source_sha256'].items():
    assert digest(OUT/'tested_bytes'/Path(name).name) == pin
unit = HERE/'stack_observer_unit_02'
assert read(unit/'terminal.json')['exit_code'] == 0
assert '13 passed' in (unit/'stdout.log').read_text(encoding='utf-8')
unit_source = read(unit/'observer_non_authoritative/source_postcheck.json')
for name,pin in unit_source['source_sha256'].items():
    assert digest(Path(name)) == pin
    assert digest(unit/'observer_non_authoritative/sampler_tested_bytes'/Path(name).name) == pin
old_helper = OUT/'tested_bytes/h1_gil_stack_observer_development_v1.py'
new_helper = REPO/'tests/h1_gil_stack_observer_development_v1.py'
assert digest(old_helper) != digest(new_helper)

bound = [Path(__file__), OUT/'plan.json', OUT/'comparison.json', OUT/'windows_crash_event.json',
    OUT/'c_timer/terminal.json', OUT/'c_timer/stack.log', OUT/'c_timer/stdout.log',
    OUT/'python_sampler/terminal.json', OUT/'python_sampler/stack.jsonl',
    OUT/'python_sampler/stdout.log', OUT/'python_sampler/result.json',
    unit/'request.json', unit/'terminal.json', unit/'stdout.log',
    unit/'observer_non_authoritative/source_postcheck.json',
    new_helper, REPO/'tests/test_h1_gil_stack_observer_development_v1.py']
bound += list((OUT/'tested_bytes').iterdir())
result = dict(status='SCOPED_SAMPLER_RACE_REPRODUCED_AND_SUCCESSOR_UNIT_CHECKS_COMPLETE',
    native_event=event, original_slice_fault_rva='0x2fbfe7',
    reproduced_fault_rva=hex(rva), same_unwind_range=['0x2fbfc0', '0x2fc4d5'],
    fault_inference='Both faults are inside the same traceback-dump function range; exact native symbols/minidump unavailable. Strong support for the asynchronous C-dump race, not an exclusion of every other native fault.',
    root_tool_terminal_observation=dict(session_id=13913, chunk_id='768d89', exit_code=0,
        source='root transcription of the actual unified-exec write_stdin result; not inferred from comparison.json',
        wall_time_seconds=0.0000084),
    plan_erratum=dict(original_field='worker_subprocesses_spawned=0',
        corrected_meaning=dict(direct_worker_processes_spawned=2, worker_descendants_spawned=0),
        original_plan_and_driver_preserved=True),
    evidence_scope=dict(pair_uses_archived_pre_cleanup_fix_helper=True,
        archived_helper_sha256=digest(old_helper), current_helper_sha256=digest(new_helper),
        current_helper_changes='receipt scope narrowed; join failures sticky with one bounded retry and status recording',
        current_helper_tests_passed=13, current_helper_test_exit_code=0,
        fresh_pair_repeated=False, full_slice_stability_verified=False),
    observed_direct_worker_pids_absent=True, official_review_verdict=None,
    full_hour0_chain_passed=False, formal_result=False, resource_admission=False,
    files_sha256={path.relative_to(REPO).as_posix():digest(path) for path in bound})
with (OUT/'postcheck_and_erratum_01.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(dict(output=str(OUT/'postcheck_and_erratum_01.json'),
    reproduced_rva=hex(rva), current_unit_tests=13, pins=len(bound))), flush=True)
