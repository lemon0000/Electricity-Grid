"""Bound one genuine owner lifecycle to test the connected path entry, without a Job."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
ENTRY = HERE.parent / 'validation_path_optimization_01/entry_revision_07'
value = json.loads((HERE / 'fresh_n0_plan_04.json').read_bytes())
assert json.loads((HERE / 'common_entry_postcheck_04_non_authoritative/terminal.json').read_bytes())['exit_code'] == 0
sources = dict(value['source_sha256'])
code = dict(value['code_lease_sha256'])
path_helper = ENTRY / 'canonical_path_lease.py'
code[str(path_helper)] = sha256(path_helper.read_bytes()).hexdigest()
sources.update(code)
for path in (Path(__file__), HERE / 'run_n0_path_entry_v1.py', HERE / 'run_n0_path_bounded_v1.py',
        REPO / 'tests/h1_gil_stack_observer_development_v1.py',
        REPO / 'tests/test_h1_registry_dispatch_probe_development_v1.py',
        HERE / 'bounded_common_arm_plan_04.json', HERE / 'bounded_common_arm_monitor_03/terminal.json',
        HERE / 'bounded_common_arm_03_non_authoritative/path_receipt.json',
        HERE / 'bounded_common_arm_03_non_authoritative/metadata_receipt.json',
        HERE / 'common_entry_postcheck_04_non_authoritative/terminal.json',
        HERE / 'fresh_n0_cap_postcheck_04_non_authoritative/terminal.json'):
    sources[str(path)] = sha256(path.read_bytes()).hexdigest()
assert all(sha256(Path(p).read_bytes()).hexdigest() == pin for p, pin in sources.items())
assert all(sha256(Path(p).read_bytes()).hexdigest() == pin for p, pin in value['old_chain_sha256'].items())
basetemp = Path('D:/h1_n0_path_owner_probe_01_non_authoritative')
value.update(question='Does the unchanged canonical path lease compose with genuine owner construction, all six raw/static checkpoints and foreign-thread rejection?',
    scope='one root genuine owner open/close and six checkpoints; zero bootstrap/Job execution',
    attempts=1, roots=1, hours=0, synthetic_jobs=0, real_native_calls=0,
    target='tests/test_h1_registry_dispatch_probe_development_v1.py',
    inner_output=str(HERE / 'n0_path_owner_probe_01_non_authoritative'),
    outer_output=str(HERE / 'n0_path_owner_probe_monitor_01'), basetemp=str(basetemp),
    source_sha256=sources, code_lease_sha256=code,
    path_roots=[str(REPO), str(basetemp)], expected_lock_count=2,
    limits=dict(wall_seconds=120, sampled_rss_bytes=768 * 1024**2, storage_bytes=128 * 1024**2),
    sampler=dict(interval_seconds=1, max_samples=1024, max_frames=128, max_bytes=16 * 1024**2,
        source_or_locals_read=False, profiling_or_trace_hook=False),
    performance_basis='same real saved common arm 33.7944072 -> 29.5464189s with exact science/full audit/metadata receipt and all cleanup; not a cold-N0 time forecast',
    dag=['fixed pins and isolated interpreter', 'bounded code entry',
        'original canonical path lease before fixture/downstream imports', 'metadata windows and stock discovery',
        'original six-checkpoint owner fixture', 'foreign scope rejected', 'owner close',
        'stop and join GIL sampler', 'path/code/hooks cleanup', 'source/old pins/process/2-lock postcheck'],
    stop='first error or 120s/768MiB/128MiB cap; preserve terminal, no extension or unchanged retry',
    whole_workflow_performance_review_complete=False)
target = HERE / 'n0_path_owner_probe_plan_01.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(value, stream, indent=2)
print(json.dumps(dict(plan_sha256=sha256(target.read_bytes()).hexdigest(),
    source_files=len(sources), code_files=len(code))))
