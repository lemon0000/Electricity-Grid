"""Preserve current child evidence and the two non-authoritative review scopes."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
entry=HERE/'run_unit_entry_v6.py';terminal_path=HERE/'canonical_path_entry6_faults_150/terminal.json'
terminal=json.loads(terminal_path.read_bytes())
assert terminal['exit_code']==0 and terminal['source_unchanged'] and terminal['observed_owned_processes_absent']
base=Path('D:/h1_path_entry6_faults_150_non_authoritative')
cases=sorted(base.glob('*/tested_child_entry.py'));assert len(cases)==10
archive=D/'canonical_path_entry6_150_preserved_non_authoritative';archive.mkdir(exist_ok=False)
copies=[]
for snapshot in cases:
    assert snapshot.read_bytes()==entry.read_bytes()
    for name in ('tested_child_entry.py','child_stdout.txt','child_stderr.txt','child_entry_source_sha256.txt',
                 'test_probe.py','launch_with_close_fault.py','child_non_authoritative/unit_code_read_lease_closed.json'):
        source=snapshot.parent/name
        if not source.exists():continue
        target=archive/snapshot.parent.name/name;target.parent.mkdir(parents=True,exist_ok=True)
        raw=source.read_bytes()
        with target.open('xb') as stream:stream.write(raw)
        assert source.read_bytes()==target.read_bytes()==raw
        copies.append(dict(source=str(source),saved=str(target),sha256=sha256(raw).hexdigest()))
paths=[entry,HERE/'run_unit_entry_v4.py',HERE/'run_unit_bounded_v19.py',Path(__file__),
    ROOT/'experiments/h1_canonical_path_lease_development_v1.py',
    ROOT/'tests/test_h1_canonical_path_unit_entry_development_v6.py',
    terminal_path,HERE/'canonical_path_entry6_faults_150/request.json',HERE/'canonical_path_entry6_faults_150/stdout.log',
    D/'canonical_path_entry6_pre_seal_input_149.json',D/'saved137_path_diagnostic_result_148.json']
paths.extend(Path(r['saved']) for r in copies)
value=dict(schema='h1_canonical_path_entry6_fix_input_151',status='PRE_SEAL_AUDIT_NONAUTHORITATIVE',
    root_sole_writer=True,files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in paths},terminal=terminal,
    child_bytes=copies,
    prior_findings=dict(reviewer='public_phase_review_118',input149_sha256=sha256((D/'canonical_path_entry6_pre_seal_input_149.json').read_bytes()).hexdigest(),
        findings=['P2: cleanup failure could bypass joint diagnostic receipt.',
                  'P2: extra-root entry CLI positive/malformed/duplicate paths insufficiently tested.']),
    fixes=['Catch errors after ExitStack has attempted all exits. Preserve original entry error, retry captured original path cleanup once, save terminal diagnostics after retry even if handles remain.',
        'Transient false/raise closes pending handles on retry but remains nonzero. Persistent false reports cleanup_failed and actual pending count, never an all-closed claim.',
        'Duplicate/missing root values rejected before opening leases. Positive extra-root route covers a mutable file outside base; unrelated same-name fixture still uses stock resolver.',
        'Normal, body primary, body+reader failure, explicit extra root, three malformed CLI cases and three CloseHandle failure modes all verified.'],
    scope='150 outer entry3 launches ten exact entry6 children;23.99s tests/26.281s outer,11 observed PIDs absent/cleanup0/source unchanged. Repo-local child evidence includes the injected launcher.',
    limitations=['Diagnostic handle-list and alias observations; no arbitrary-memory or path ABA proof.',
        'Persistent injected path failure retains pending handles until child process exit and is explicitly nonzero; not graceful successful cleanup.',
        '148 performance applies to prior entry6 success bytes. Current changes affect failure handling and CLI validation; current public execution and complete workflow still unverified.'],
    original_entry4_and_path_helper_unchanged=True,production_seal=False,official_review=False,
    whole_workflow_performance_review_complete=False,full_optimized_workflow_accepted=False,
    formal_result=False,formal_execution_ready=False,resource_admission=False,native_execution_authorized=False)
out=D/'canonical_path_entry6_fix_input_151.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
prior=D/'public_phase_fix_input_135.json'
notes=dict(schema='h1_public_phase_135_scoped_findings_note',status='NONAUTHORITATIVE_NAMED_CLOSURE',
    reviewer='public_phase_review_118',input_sha256=sha256(prior.read_bytes()).hexdigest(),
    source='Transcription of the existing independent reviewer findings, reconfirmed during149 review; not a new official review.',
    closed=['Owner identity maps:12899 cases; id/weakref/token maps and actual MRO hash/eq pins.',
        'Creator-thread LIFO isolation:13232 cases plus134 broad regression.',
        'First raw entry failure:13314 cases plus134 broad regression.'],
    regression=dict(cases=116,terminal_exit=0,source_unchanged=True,observed_PIDs_absent=True,cleanup_errors=0),
    open=['Positive genuine public N0 return with terminal, numerical oracle and closure.',
        'Complete typed optimized chain, whole-workflow budget and formal acceptance.'],
    official_review=False,production_seal=False,formal_result=False,resource_admission=False)
note=D/'public_phase_scoped_findings_135_reconfirmed_149.json'
with note.open('x',encoding='utf-8',newline='\n') as stream:json.dump(notes,stream,indent=2);stream.write('\n')
print(json.dumps(dict(input=str(out),sha256=sha256(out.read_bytes()).hexdigest(),preserved=len(copies),
                      prior_findings=str(note),prior_findings_sha256=sha256(note.read_bytes()).hexdigest())))
