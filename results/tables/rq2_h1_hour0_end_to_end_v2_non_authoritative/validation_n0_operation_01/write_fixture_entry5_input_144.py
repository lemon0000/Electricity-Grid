"""PRE_SEAL evidence for metadata fixture windows; no production receipt."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
old=HERE/'run_unit_entry_v4.py';new=HERE/'run_unit_entry_v5.py'
monitor_old=HERE/'run_unit_bounded_v17.py';monitor_new=HERE/'run_unit_bounded_v18.py'
assert monitor_new.read_text()==monitor_old.read_text().replace('run_unit_entry_v4.py','run_unit_entry_v5.py')
base=Path('D:/h1_fixture_metadata_143_non_authoritative')
snapshots=list(base.glob('*/tested_child_entry.py'));assert len(snapshots)==4
assert all(p.read_bytes()==new.read_bytes() for p in snapshots)
terminal_path=HERE/'fixture_metadata_entry5_units_143/terminal.json';terminal=json.loads(terminal_path.read_bytes())
assert terminal['exit_code']==0 and terminal['source_unchanged'] and terminal['observed_owned_processes_absent']
paths=[old,new,monitor_old,monitor_new,Path(__file__),ROOT/'tests/test_h1_metadata_fixture_windows_entry_development_v5.py',
    HERE/'fixture_metadata_entry5_units_143/request.json',terminal_path,HERE/'fixture_metadata_entry5_units_143/stdout.log']
paths.extend(HERE.parent/'validation_path_optimization_01/entry_revision_14_non_authoritative'/name for name in
    ('pinned_distribution_resolver_v1.py','metadata_parse_lease.py','code_read_lease.py'))
paths.extend(snapshots)
for path in base.glob('*/child_non_authoritative/unit_code_read_lease_closed.json'):paths.append(path)
value=dict(schema='h1_fixture_metadata_entry5_pre_seal_input_144',status='PRE_SEAL_AUDIT_NONAUTHORITATIVE',
    root_sole_writer=True,files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in paths},terminal=terminal,
    changes=['Original per-body resolver kept; add independent scopes for example/setup/numerical/prepared fixtures.',
        'Nested dynamic fixture requests borrow the outer scope rather than nesting a one-shot resolver.',
        'Persist closed diagnostic receipt and validation errors before returning nonzero when a fixture body fails. Do not ignore poisoned resolver cleanup or incomplete bookends.'],
    unchanged='Original metadata/code helpers, native discovery oracles, fallback behavior, version function and scientific modules unchanged.',
    tests=['normal fixture version and distinct fresh body resolver',
        'unknown package native fallback',
        'fixture body exception preserves failure, aliases/cache/OS handles restore; failed exit discovery remains explicitly incomplete with nonzero status',
        'sys.path drift keeps native fallback',
        'dynamic nested setup borrows prepared scope and no second fixture scope opens'],
    failures_preserved={'139':'pytest metadata is outside the eight pinned package names; test fast-path expectation was invalid.',
        '140':'lowercase pyomo intentionally falls back because selected key is Pyomo; use exact pinned numpy for the fast path.',
        '141/142':'Fixture error poisoned the original resolver and caused exit oracle refusal; entry assertions lost the diagnostic receipt. New entry persists the full failed receipt and returns nonzero.'},
    current_bodies=4,external_child_entry_snapshots_match=True,
    scope='Unit entry composition only; real saved-candidate numerical differential and actual fixture cost not measured yet.',
    production_seal=False,official_review=False,whole_workflow_performance_review_complete=False,
    formal_result=False,formal_execution_ready=False,resource_admission=False,native_execution_authorized=False)
out=D/'fixture_metadata_entry5_pre_seal_input_144.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest())))
