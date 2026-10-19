"""Bind fixes to the independent findings on112; diagnostic review only."""
from hashlib import sha256
import difflib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
prior_path=D/'shared_phase_scope_pre_seal_input_112.json'
prior=json.loads(prior_path.read_text());terminal=json.loads((HERE/'shared_phase_scope_review_fixes_114/terminal.json').read_text())
assert terminal['exit_code']==0 and terminal['source_unchanged'] and terminal['observed_owned_processes_absent']
assert not terminal['cleanup_errors'] and not terminal['storage_read_errors']
assert terminal['storage_observation_contract']=='no_follow_reparse_entries'
files=[p for p in prior['files_sha256'] if '/shared_phase_scope_hardening_112/' not in p]
files.extend(['tests/test_h1_unit_storage_observer_development_v16.py',
    (HERE/'run_unit_bounded_v15.py').relative_to(ROOT).as_posix(),
    (HERE/'run_unit_bounded_v16.py').relative_to(ROOT).as_posix()])
for name in ('request.json','started.json','terminal.json','stdout.log'):
    files.append((HERE/'shared_phase_scope_review_fixes_114'/name).relative_to(ROOT).as_posix())
delta=''.join(difflib.unified_diff((HERE/'run_unit_bounded_v15.py').read_text().splitlines(True),
    (HERE/'run_unit_bounded_v16.py').read_text().splitlines(True),fromfile='runner15',tofile='runner16'))
value=dict(schema='h1_shared_phase_scope_pre_seal_input_114',status='DRAFT_NONAUTHORITATIVE',
    predecessor_input_sha256=sha256(prior_path.read_bytes()).hexdigest(),root_is_sole_writer=True,
    files_sha256={p:sha256((ROOT/p).read_bytes()).hexdigest() for p in files},
    acceptance=prior['acceptance'],independent_pre_seal_findings_only=True,
    fixes=[
       dict(id='112-P1-dangling-route',finding='exists follows dangling junctions and may hide existing reparse entries',
            change='Call the original non-following _plain for root and every parent; skip only FileNotFoundError with errno ENOENT',
            tests='entry/exit by root/parent: four actual dangling-junction negatives'),
       dict(id='112-P1-path-descriptors',finding='Path structural descriptors were not definition-bound',
            change='Pin actual MRO owner descriptors for division, parents, absolute test, anchor, parts, relative test, equality and hashing',
            tests='eight independent pre-acquisition descriptor identity negatives'),
       dict(id='112-P2-outer-orphan',finding='outer abandonment with first CloseHandle failure not composed',
            change='Add outer GC, one retained kernel orphan, exact one-handle bounded retry and zero actual handles test',
            tests='outer owner weak reference clears; active0/pending1; retry closes exactly one and pending0'),
    ],
    monitor_successor=dict(from_version=15,to_version=16,diff=delta,
       reason='Windows os.walk follows junction directory entries despite followlinks=False; cycles/broken targets stopped111/113',
       policy='Scandir and stat each entry without following; enqueue only ordinary non-reparse directories; preserve real observation failures',
       tests='actual cycle/broken/external-target junctions plus nested ordinary files; visit only two owned directories; permission errors remain failures'),
    failed_attempts_preserved=['shared_phase_scope_hardening_111','shared_phase_scope_findings_113'],
    terminal=terminal,unit_bodies='39 passed in 29.79s',
    remaining_open=prior['remaining_open'],formal_result=False,formal_execution_ready=False,
    resource_admission=False,native_execution_authorized=False,official_review=False,formal_run_authorized=False)
out=D/'shared_phase_scope_pre_seal_input_114.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest())))
