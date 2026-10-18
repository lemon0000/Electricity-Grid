"""One short observable prefix after plan03 reached its wall cap without samples."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
value = json.loads((HERE / 'parent_inspection_footprint_plan_03.json').read_bytes())
prior = json.loads((HERE / 'parent_inspection_footprint_monitor_03/terminal.json').read_bytes())
assert prior['stop_reason'] == 'wall' and prior['observed_owned_processes_absent']
assert prior['source_unchanged'] and prior['old_chain_unchanged'] and prior['saved_files_unchanged']
sources = {name: sha256(Path(name).read_bytes()).hexdigest() for name in value['source_sha256']}
for path in (Path(__file__), HERE / 'measure_parent_inspection_footprint_v4.py',
        HERE / 'run_parent_inspection_footprint_bounded_v4.py',
        REPO / 'tests/h1_gil_stack_observer_development_v1.py',
        HERE / 'parent_inspection_footprint_monitor_03/terminal.json'):
    sources[str(path)] = sha256(path.read_bytes()).hexdigest()
for name, pin in {**value['saved_sha256'], **value['old_chain_sha256']}.items():
    assert sha256(Path(name).read_bytes()).hexdigest() == pin
value.update(question='Locate the nested numerical source bottleneck from a bounded observable inspection prefix',
    source_sha256=sources, attempts=1, measurement_seconds=20,
    inner_output=str(HERE / 'parent_inspection_footprint_04_non_authoritative'),
    outer_output=str(HERE / 'parent_inspection_footprint_monitor_04'),
    basetemp='D:/h1_parent_inspection_footprint_04_non_authoritative',
    changed_input_reason='plan03 emitted no partial samples before cap; this instrumentation persists a 20-second GIL stack and read prefix and stops at the next open event',
    whole_inspection_completion_required=False,
    full_Parent_optimization_admitted=False,
    dag=['fixed prior capped outcome, source pins, compatible immutable snapshot and saved bytes',
        'unchanged entry07 code/metadata leases and repo-only path lease',
        'one original conditional inspection, at most a 20-second observed business prefix',
        'persist partial open events and GIL-only samples even on deliberate stop',
        'unwind original contexts and verify code/path restoration and code handle release',
        'outer verifies saved183/source/old36 and owned process absence'],
    limits=dict(wall_seconds=75, sampled_rss_bytes=768*1024**2, storage_bytes=128*1024**2))
path = HERE / 'parent_inspection_footprint_plan_04.json'
with path.open('x', encoding='utf-8') as stream:
    json.dump(value, stream, indent=2)
print(json.dumps(dict(plan_sha256=sha256(path.read_bytes()).hexdigest(),
    measurement_seconds=value['measurement_seconds'], limits=value['limits'])))
