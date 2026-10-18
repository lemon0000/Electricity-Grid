"""Bound the actual Parent-alias v3 tests to the already tested configured entry."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
base = json.loads((HERE / 'n0_path_owner_probe_plan_02.json').read_bytes())
sources = dict(base['source_sha256'])
code = dict(base['code_lease_sha256'])
for path in (REPO / 'experiments/h1_selector_phase_handoff_development_v3.py',
        REPO / 'tests/test_h1_selector_phase_handoff_negative_development_v1.py'):
    code[str(path)] = sha256(path.read_bytes()).hexdigest()
sources.update(code)
for path in (Path(__file__), HERE / 'run_negative_handoff_alias_bounded_v2.py',
        HERE / 'run_n0_path_entry_v1.py', HERE / 'n0_path_owner_probe_monitor_01/terminal.json',
        HERE / 'n0_path_owner_probe_01_non_authoritative/path_closed_receipt.json',
        HERE / 'negative_handoff_unit_01/terminal.json',
        REPO / 'tests/h1_group_selector_integration_helpers_v3.py',
        REPO / 'tests/test_h1_hour0_end_to_end_development_v3.py',
        REPO / 'docs/model_spec/rq2_h1_negative_actual_precheck_development_v1.md'):
    sources[str(path)] = sha256(path.read_bytes()).hexdigest()
profiler=Path('D:/Miniconda3/envs/compute/Scripts/py-spy.exe')
sources[str(profiler)]=sha256(profiler.read_bytes()).hexdigest()
assert all(sha256(Path(p).read_bytes()).hexdigest() == pin for p, pin in sources.items())
assert all(sha256(Path(p).read_bytes()).hexdigest() == pin for p, pin in base['old_chain_sha256'].items())
assert json.loads((HERE / 'n0_path_owner_probe_monitor_01/terminal.json').read_bytes())['exit_code'] == 0
basetemp = Path('D:/h1_negative_handoff_alias_03_non_authoritative')
value = dict(question='Does the real Parent-alias reference permit Handoff v3 to reject missing-all without any Actual creation or common replay, and what CPU paths appear in its first90s sampled prefix?' ,
    status='DRAFT_NONAUTHORITATIVE', attempts=1, synthetic_jobs=0, real_native_calls=0,
    target='tests/test_h1_selector_phase_handoff_negative_development_v1.py::test_missing_all_rejects_without_creating_any_actual',
    source_sha256=sources, code_lease_sha256=code, old_chain_sha256=base['old_chain_sha256'],
    profiler=dict(executable=str(profiler),duration_seconds=90,rate=49,format='raw',gil_only=True,nonblocking=True),
    inner_output=str(HERE / 'negative_handoff_alias_03_non_authoritative'),
    outer_output=str(HERE / 'negative_handoff_alias_monitor_03'), basetemp=str(basetemp),
    path_roots=[str(REPO), str(basetemp)], minimum_lock_count=3,
    limits=dict(wall_seconds=180, sampled_rss_bytes=1024**3, storage_bytes=128 * 1024**2),
    source_and_execution_seams='explicit synthetic source and in-process fake Parent lifecycle/native solver; original selector archive and phase persistence/replay code',
    previous_attempt='configured alias01 capped240.375s during first Actual before reaching rejection; preserve snapshot, separate fail-first target rather than extend cap',
    changed_path='same configured entry; reject missing-all before any Actual creation; external read-only nonblocking CPU sampling, no Python profile/trace hooks',
    dag=['fixed source and unused roots', 'already verified configured entry',
        'reference Parent alias using in-process fake lifecycle',
        'missing-all before creating any Actual; unchanged common replay counter and no root',
        'single-attempt failure and original guards released', 'all owners close',
        'stop/join sampler and release path/code/metadata resources', 'all sources/old pins/PIDs/discovered locks postcheck'],
    stops='first error or fixed180s/1GiB sampled RSS/128MiB; no extension or unchanged retry',
    full_hour0_chain_passed=False, whole_workflow_performance_review_complete=False,
    formal_result=False, resource_admission=False, native_execution_authorized=False)
target = HERE / 'negative_handoff_alias_plan_03.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(value, stream, indent=2)
print(json.dumps(dict(plan_sha256=sha256(target.read_bytes()).hexdigest(), source_files=len(sources), code_files=len(code))))
