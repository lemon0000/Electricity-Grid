"""Portable pre-seal inputs for entry6 composition, not a production receipt."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
old=HERE/'run_unit_entry_v4.py';new=HERE/'run_unit_entry_v6.py'
monitor=HERE/'run_unit_bounded_v19.py'
assert monitor.read_text()==(HERE/'run_unit_bounded_v17.py').read_text().replace('run_unit_entry_v4.py','run_unit_entry_v6.py')
terminal_path=HERE/'canonical_path_entry6_units_147/terminal.json'
terminal=json.loads(terminal_path.read_bytes())
assert terminal['exit_code']==0 and terminal['source_unchanged'] and terminal['observed_owned_processes_absent']
base=Path('D:/h1_path_entry6_units_147_non_authoritative')
cases=sorted(base.glob('*/tested_child_entry.py'));assert len(cases)==3
archive=D/'canonical_path_entry6_147_preserved_non_authoritative';archive.mkdir(exist_ok=False)
copies=[]
for entry in cases:
    assert entry.read_bytes()==new.read_bytes()
    for name in ('tested_child_entry.py','child_stdout.txt','child_stderr.txt',
                 'child_entry_source_sha256.txt','test_probe.py',
                 'child_non_authoritative/unit_code_read_lease_closed.json'):
        source=entry.parent/name;target=archive/entry.parent.name/name
        raw=source.read_bytes();target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:stream.write(raw)
        assert target.read_bytes()==raw and source.read_bytes()==raw
        copies.append(dict(source=str(source),saved=str(target),sha256=sha256(raw).hexdigest()))
paths=[old,new,monitor,HERE/'run_unit_bounded_v17.py',HERE/'build_path_unit_entry_v6.py',Path(__file__),
       ROOT/'tests/test_h1_canonical_path_unit_entry_development_v6.py',
       ROOT/'experiments/h1_canonical_path_lease_development_v1.py',
       ROOT/'tests/test_h1_canonical_path_lease_development_v1.py',
       terminal_path,HERE/'canonical_path_entry6_units_147/request.json',
       HERE/'canonical_path_entry6_units_147/stdout.log',D/'saved137_n0_operation_diagnostic_result_146.json',
       D/'saved137_path_diagnostic_plan_148.json']
paths.extend(Path(r['saved']) for r in copies)
value=dict(schema='h1_canonical_path_entry6_pre_seal_input_149',status='PRE_SEAL_AUDIT_NONAUTHORITATIVE',
    root_sole_writer=True,files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in paths},
    child_bytes=copies,terminal=terminal,
    scope='Compose unchanged CanonicalPathLease into entry4, before test/fixture imports, with explicit REPO/base/optional bounded extra root. No entry5 fixture hooks.',
    changes=['Entry6 and monitor19 are non-authoritative diagnostics; original entry4/helper unchanged.',
        'Leaf lstat/file bytes and ancestor reparse/case observations remain fresh; only original path traversal is reused.',
        'Write joint path/code/metadata close state. Capture resolver reader errors separately; preserve original body primary and nonzero.',
        'Three child cases cover normal mutable file reads, body primary, combined body and resolver Runtime/reader failure. Same-name unrelated fixture keeps stock metadata resolver.'],
    tests='147 exit0,3 passed10.75s, source unchanged, four observed PIDs absent, cleanup0; exact child stdout/stderr/entry/closed/probe bytes saved repo-local.',
    performance='146 baseline151.08s/outer153.984s complete.148 same-program path composition running; no performance conclusion yet.',
    open_limits=['No public Bootstrap return/retained heads/N0 registration proof.',
        'No complete optimized typed chain or whole-workflow budget.',
        'Process-tree absence and path ABA are not proven; sampled memory/storage only.'],
    production_seal=False,official_review=False,whole_workflow_performance_review_complete=False,
    full_optimized_workflow_accepted=False,formal_result=False,formal_execution_ready=False,
    resource_admission=False,native_execution_authorized=False)
target=D/'canonical_path_entry6_pre_seal_input_149.json'
with target.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(target),sha256=sha256(target.read_bytes()).hexdigest(),preserved=len(copies))))
