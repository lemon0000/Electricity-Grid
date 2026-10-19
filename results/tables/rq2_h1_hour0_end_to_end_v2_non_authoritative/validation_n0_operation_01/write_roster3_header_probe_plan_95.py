"""Fix the zero-N0 header diagnostic question and budget before launch."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys

H = Path(__file__).resolve().parent
R = H.parents[3]
D = H / 'whole_workflow_optimization_01_non_authoritative'
E = H.parent / 'validation_path_optimization_01/entry_revision_14_non_authoritative'
pin = lambda p: sha256(p.read_bytes()).hexdigest()
outer = H / 'workflow_typed_header_entry_units_94'
child = E / 'typed_header_entry_units_94'
terminal = json.loads((outer / 'terminal.json').read_bytes())
assert terminal['exit_code'] == 0 and terminal['source_unchanged']
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']
assert 'Ran 145 tests' in (child / 'unittest.log').read_text(encoding='utf-8')
label, child_label = 'workflow_roster3_header_95', 'roster3_header_95'
base = Path('D:/h1_wf14_' + child_label + '_non_authoritative')
assert not any(p.exists() for p in (H / label, E / child_label, base))
paths = {p for p in E.iterdir() if p.is_file()} | {
    Path(__file__), Path(sys.executable), H / 'run_workflow_entry_bounded_v8.py',
    H / 'build_typed_header_entry_draft_v2.py'}
for name, key in [('code_allowlist_v3.json', 'files_sha256'),
        ('vendor_code_allowlist_v1.json', 'files_sha256'),
        ('metadata_allowlist_v1.json', 'files_sha256')]:
    for name, expected in json.loads((E / name).read_bytes())[key].items():
        p = Path(name)
        assert pin(p) == expected
        paths.add(p)
for name, expected in json.loads((E / 'test_closure_v1.json').read_bytes())['files_sha256'].items():
    p = R / name
    assert pin(p) == expected
    paths.add(p)
for name, row in json.loads((E / 'scientific_input_allowlist_v1.json').read_bytes())['files'].items():
    p = Path(name)
    assert pin(p) == row['sha256']
    paths.add(p)
paths |= {outer / n for n in ('request.json', 'started.json', 'terminal.json')}
paths |= {child / n for n in ('request.json', 'terminal.json', 'unittest.log')}
paths |= {D / n for n in ('typed_header_entry_completion_and_rework_93.json',
    'retained_registry_multiplier_audit_01.json', 'roster3_live_header_guarded_read_failure_91.json')}
for field, path in [('request_sha256', outer / 'request.json'),
        ('started_sha256', outer / 'started.json'),
        ('runner_sha256', H / 'run_workflow_entry_bounded_v8.py')]:
    assert terminal[field] == pin(path)
command = [str(Path(sys.executable)), '-B', str(H / 'run_workflow_entry_bounded_v8.py'),
    label, '300', '1024', '128', '--', '-I', str(E / 'launch_validation.py'),
    'pytest', 'parse_path', child_label, 'tests/test_h1_roster3_live_header_development_v1.py']
result = dict(status='BOUNDED_DIAGNOSTIC_PLAN_NONAUTHORITATIVE', risk='R3',
    created_at_utc=datetime.now(timezone.utc).isoformat(),
    question='Does exact Bootstrap4/Roster3 empty-registry header create/inspect/guard/close/reopen finish within300s in configured entry14?',
    command=command, attempt_label=label, child_label=child_label, test=command[-1],
    scale=dict(cases=1, bootstrap_owners_sequential=2, roster_owners_sequential=2,
        completed_releases=0, new_N0_Jobs=0, native_calls=0),
    dag=['static synthetic fixture and new Bootstrap4 profile/declaration',
        'exact Bootstrap4 header create', 'Roster3 header create and inspect',
        'guard competition and foreign-thread rejection', 'all original close',
        'fresh Bootstrap4/Roster3 reopen and inspect equality',
        'close; denial counters; observation JSON; pytest/entry cleanup; terminal/source/process readback'],
    performance=dict(hypothesis='Reuse tested static-code/metadata/distribution/scientific-byte entry caches; no owner/registry/terminal/source-value cache',
        prior='91 failed at unguarded test journal access after create/inspect/guard; not a passed lifecycle or runtime baseline',
        counts='k=0: no foreign N0 prepares; header costs only; no genuine graph or whole-chain ETA'),
    limits=dict(wall_seconds=300, sampled_rss_bytes=1024**3, storage_bytes=128*1024**2,
        concurrency=1, retries=0, progress='stage JSON with elapsed time and runner liveness/CPU/RSS/storage samples',
        stop='fixed wall/RSS/storage cap or child exit; observed owned PID+creation cleanup; cap is not extended',
        no_progress='No stage for120s triggers inspection, not a dead-loop claim; hard300s cap remains'),
    execution_denial_seams=['bootstrap', 'attach', 'controller', 'source', 'external_data', 'solver', 'stage', 'capture', 'job'],
    acceptance=['exit0 and single test passed', 'all9 expected stages and exact inspect view after reopen',
        'all9 denial counters observed zero', 'original guards released and all4 owners closed',
        'source/test/package/env pins unchanged; cleanup/storage complete; observed PID+creation absent'],
    entry_package_sha256=pin(E / 'package_manifest_v1.json'),
    files_sha256={str(p): pin(p) for p in sorted(paths)},
    environment=dict(interpreter=str(Path(sys.executable)), interpreter_sha256=pin(Path(sys.executable)),
        version=sys.version, platform=platform.platform(), timezone='Asia/Shanghai'),
    evidence_reused=['legacy chain07 body and supplement04 closed', '87 Roster3 data checks',
        '89 projector156 and92 extra6', '94 package145 cases,1skip,0failures'],
    bounded_diagnostic_self_review_complete=True, whole_workflow_performance_review_complete=False,
    full_optimized_workflow_accepted=False, completed_N0_attach_positive=False,
    production_seal=False, official_review=False, formal_result=False,
    formal_execution_ready=False, resource_admission=False, native_execution_authorized=False)
path = D / 'roster3_header_probe_plan_95.json'
with path.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(dict(path=str(path), sha256=pin(path), pins=len(paths))))
