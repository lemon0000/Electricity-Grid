"""Root-only append of draft progress after terminal tests; never opens a gate."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
def digest(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(path.read_bytes())
def new(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False);stream.write('\n')

previous=ROOT/'results/tables/rq2_h1_selector_phase_consumption_v1_non_authoritative/development_checks.json'
old=read(previous)
files=['experiments/h1_selector_phase_handoff_development_v1.py',
       'docs/model_spec/rq2_h1_selector_phase_handoff_development_v1.md']
files += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'tests').glob('test_h1_selector_phase_handoff*_development_v1.py'))]
pins=old['files_sha256']|{p:digest((ROOT/p).read_bytes()) for p in files}
assert all(digest((ROOT/p).read_bytes())==pin for p,pin in pins.items())
evidence_names=['root_faults_integrity_07.json','root_integration_08.json','root_related_10.json',
                'root_caps_11.json','root_bundle_12.json','root_holder_14.json','independent_tests_13.json']
tests={name:read(HERE/name) for name in evidence_names}
for name,result in tests.items():
    assert result['exit_code']==0,(name,result['output'])
    if 'before' in result:
        assert result['before']==result['after']
        assert all(digest((ROOT/p).read_bytes())==pin for p,pin in result['after'].items())
assert all(digest((ROOT/p).read_bytes())==pin for p,pin in tests['independent_tests_13.json']['root_fresh_pins'].items())
remaining=['all-paired multi-Actual persistent integration',
           'durable global-chain ancestry beyond the explicit fixture history',
           'parent/source archive drift after takeover with actual Parent alias replay',
           'remaining applicable reparse and nested original-handle ownership checks',
           'independent F6 matrix closure before development closure',
           'hour1+/192-hour producer integration and typed failed-Actual evidence',
           'task/reuse DAG, same-contract LB/UB, full resource admission, successor seal and fresh official review',
           'specific new native authorization for the concrete admitted package']
flags={k:v for k,v in read(ROOT/'results/tables/rq2_h1_bootstrap_integration_v1_non_authoritative/draft_state_23.json').items()
       if type(v) is bool}
progress=dict(schema='h1_selector_phase_handoff_draft_progress_v1',status='DRAFT_NONAUTHORITATIVE_F6_OPEN',
    scope='hour-0 live-Parent/common handoff draft with fault-tested persistence; pre-seal verification incomplete',
    previous_checks_path=previous.relative_to(ROOT).as_posix(),previous_checks_sha256=digest(previous.read_bytes()),
    pin_count=len(pins),files_sha256=pins,
    evidence_files_sha256={p.name:digest(p.read_bytes()) for p in sorted(HERE.glob('*.json'))},
    final_root_tests={name:dict(exit_code=result['exit_code'],output=result['output']) for name,result in tests.items()},
    static_implementation_findings_closed=['phase DB/root/lock identity continuity','binding exact first readback',
                                         'external callback token and closure-owned counters'],
    preseal_findings_closed=False,F6_closed=False,remaining=remaining,unit_real_native_calls=0,unit_windows_jobs=0,
    historical_authority_incident='results/tables/rq2_h1_selector_launch_preparation_v1_non_authoritative/native_boundary_incident_01/incident.json',
    **flags)
progress_path=HERE/'development_progress_01.json'
draft_path=ROOT/'results/tables/rq2_h1_bootstrap_integration_v1_non_authoritative/draft_state_24.json'
trace_path=HERE/'append_trace_01.json'
assert not any(p.exists() for p in (progress_path,draft_path,trace_path))
prior_trace=read(ROOT/'results/tables/rq2_h1_selector_phase_consumption_v1_non_authoritative/append_trace_01.json')
originals=[]
for item in prior_trace['documents']:
    path=ROOT/item['path'];raw=path.read_bytes()
    assert digest(raw)==item['after_sha256']
    originals.append((path,raw))
new(progress_path,progress)
new(draft_path,dict(status='DRAFT_NONAUTHORITATIVE',scope=progress['scope'],
    development_progress_path=progress_path.relative_to(ROOT).as_posix(),
    development_progress_sha256=digest(progress_path.read_bytes()),remaining=remaining,**flags))
addition=(
    '\n\n### 2026-10-12 - Live selector phase handoff draft; F6 verification remains open\n\n'
    'Developed experiments/h1_selector_phase_handoff_development_v1.py and six scoped test files. '
    'The draft holds exact Parent/common guards through raw replay, retained takeover intent, holder preparation, '
    'paired SQLite commit and readback. It preserves unresolved business lanes and requires complete lane dispositions. '
    'Independent static review found and the draft repaired phase DB/root/lock identity continuity across close-reopen, '
    'binding first raw readback equality, and callback reentry through mutable flags or exposed state helpers; '
    'external state/counts now use closure records and a per-call token. Historical drafts and failures remain preserved.\n\n'
    'Current root evidence: faults/integrity 68 passed; actual Parent-alias integration 2 passed '
    '(including mixed paired/unresolved lanes and captured global ancestor); capacity 4 passed; bundle/roster 4 passed; '
    'holder identity 3 passed; related preview/phase-owner 36 passed. Independent targeted 14 passed/28 deselected, '
    '140.09s, exit0, unchanged hashes. These fabricated solver/source/lifecycle and explicit synthetic Parent tests '
    'are development evidence only: this unit uses zero real native and zero Windows Jobs. The prior legacy-worker '
    'native-authority incident remains preserved and excluded.\n\n'
    f'Evidence: {progress_path.relative_to(ROOT).as_posix()}, SHA256 {digest(progress_path.read_bytes())}, '
    f'{len(pins)} pins; draft_state_24 SHA256 {digest(draft_path.read_bytes())}. '
    'Predecessor1042 pins, old v2/v3 outer895/1695 and run248/251 remain unchanged. '
    'This is not PRE_SEAL closure or an official verdict. F6 remains open for all-paired multi-Actual integration, '
    'durable global ancestry beyond fixture history, post-takeover parent/source archive drift, and remaining applicable '
    'reparse/nested ownership checks. Next close that evidence matrix before promoting this development unit. '
    'Hour1+/192-hour integration, typed failed Actual, actual task/reuse DAG, same-contract LB/UB, resource admission, '
    'successor sealing and a fresh official review remain open. New real native requires specific authorization '
    'for an admitted concrete package. All formal/resource/execution/phase-consumption gates remain false.\n'
).encode('utf-8')
documents=[]
for path,before in originals:
    with path.open('ab') as stream:stream.write(addition)
    after=path.read_bytes();assert after==before+addition
    documents.append(dict(path=path.relative_to(ROOT).as_posix(),before_sha256=digest(before),
                          after_sha256=digest(after),original_bytes_preserved=True))
new(trace_path,dict(documents=documents,development_progress_sha256=digest(progress_path.read_bytes()),
                    draft_state_sha256=digest(draft_path.read_bytes())))
print(json.dumps(dict(progress_sha256=digest(progress_path.read_bytes()),pin_count=len(pins),
                      draft_state_sha256=digest(draft_path.read_bytes()),preseal_findings_closed=False)))
