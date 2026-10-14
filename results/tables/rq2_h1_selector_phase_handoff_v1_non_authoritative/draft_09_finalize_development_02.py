"""Root-only non-authoritative evidence publication after terminal review.

Never creates a production seal, review receipt or native execution authority.
"""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
def digest(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(path.read_bytes())
def new(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False);stream.write('\n')

expected={'root_faults_20.json':34,'root_multi_actual_21.json':1,
          'root_actual_drift_24.json':3,'root_global_25.json':2,
          'root_regression_26.json':76,'root_reference_drift_27.json':3,
          'root_integration_28.json':2,'root_real_roster_31.json':2}
independent={'independent_tests_23.json':6,'independent_global_29.json':2,
             'independent_resources_30.json':25,'independent_real_roster_32.json':2}
tests={}
for name,count in (expected|independent).items():
    result=read(HERE/name)
    assert result['exit_code']==0,(name,result['output'])
    assert int(re.search(r'(\d+) passed',result['output']).group(1))==count
    assert result['before']==result['after']
    assert all(digest((ROOT/p).read_bytes())==pin for p,pin in result['after'].items())
    tests[name]=dict(passed=count,exit_code=0,output=result['output'])
review=read(HERE/'preseal_closure_33.json')
assert review['scoped_development_findings_closed'] is True and review['official_verdict'] is False
assert all(digest((ROOT/p).read_bytes())==pin for p,pin in review['files_sha256'].items())
previous=ROOT/'results/tables/rq2_h1_selector_phase_consumption_v1_non_authoritative/development_checks.json'
old=read(previous)
files=['experiments/h1_selector_phase_handoff_development_v1.py',
       'docs/model_spec/rq2_h1_selector_phase_handoff_development_v1.md']
files += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'tests').glob('test_h1_selector_phase_handoff*_development_v1.py'))]
pins=old['files_sha256']|{p:digest((ROOT/p).read_bytes()) for p in files}
assert all(digest((ROOT/p).read_bytes())==pin for p,pin in pins.items())
assert read(HERE/'predecessor_verification_22.json')['drift']==[]
prior=read(HERE/'append_trace_01.json');originals=[]
for item in prior['documents']:
    path=ROOT/item['path'];raw=path.read_bytes()
    assert digest(raw)==item['after_sha256']
    originals.append((path,raw))
flags={k:v for k,v in read(ROOT/'results/tables/rq2_h1_bootstrap_integration_v1_non_authoritative/draft_state_24.json').items() if type(v) is bool}
remaining=['canonical complete GroupRoster/common scientific correspondence',
           'hour1+/192-hour N-to-Rref-to-business/Actual producer integration',
           'typed failed-Actual observation and consumption semantics',
           'canonical Parent/Windows Job/native provenance and complete timing/resource admission',
           'actual task/reuse DAG, same-contract LB/UB, successor seal and fresh official review',
           'specific new native authorization for the concrete admitted package']
checks=dict(schema='h1_selector_phase_handoff_checks_v1',status='PRE_SEAL_HANDOFF_SCOPED_FINDINGS_CLOSED',
    scope='hour-0 live Parent/common handoff implementation; synthetic Parent/solver/source evidence, real persistent stores and separately real journal/roster lifetime tests',
    previous_checks_path=previous.relative_to(ROOT).as_posix(),previous_checks_sha256=digest(previous.read_bytes()),
    historical_progress_path=(HERE/'development_progress_01.json').relative_to(ROOT).as_posix(),
    historical_progress_sha256=digest((HERE/'development_progress_01.json').read_bytes()),
    pin_count=len(pins),files_sha256=pins,root_tests_passed=sum(expected.values()),
    independent_tests_passed=sum(independent.values()),terminal_tests=tests,
    evidence_files_sha256={p.name:digest(p.read_bytes()) for p in sorted(HERE.glob('*.json'))},
    scoped_development_findings_closed=True,remaining=remaining,
    unit_real_native_calls=0,unit_windows_jobs=0,
    historical_authority_incident='results/tables/rq2_h1_selector_launch_preparation_v1_non_authoritative/native_boundary_incident_01/incident.json',
    **flags)
check_path=HERE/'development_checks.json'
draft_path=ROOT/'results/tables/rq2_h1_bootstrap_integration_v1_non_authoritative/draft_state_25.json'
trace_path=HERE/'append_trace_02.json'
assert not any(p.exists() for p in (check_path,draft_path,trace_path))
new(check_path,checks)
new(draft_path,dict(status='DRAFT_NONAUTHORITATIVE',scope=checks['scope'],
    development_checks_path=check_path.relative_to(ROOT).as_posix(),development_checks_sha256=digest(check_path.read_bytes()),
    remaining=remaining,**flags))
addition=(
    '\n\n### 2026-10-12 - Hour-zero selector phase handoff scoped development reviewed\n\n'
    'The handoff now captures original nested leases, streams, aliases and acquired guards for cleanup. '
    'Before takeover, every external callback failure restores captured references and freshly revalidates leases and the durable common view, '
    'including deleted fields and durable-only corruption; integrity loss poisons the borrowed capability without automatic close, reconstruction or retry. '
    'After takeover, cleanup releases only captured original resources. No automatic head adoption or recovery is introduced.\n\n'
    f'Final-byte root tests: {sum(expected.values())} passed across all eleven handoff test files; independent {sum(independent.values())} passed, all terminal exit0 with unchanged relevant hashes. '
    'Coverage includes two complete Actual Parents sharing one exact Rref, mixed paired/unresolved lanes, reference/Actual archive drift, '
    'real retained global-journal ancestry, operation-time head drift, and real GroupRoster three-original-guard acquisition/release with foreign-lock protection. '
    'Parent/solver/source scientific inputs remain explicit synthetic seams; the real roster test proves metadata/lifetime only. '
    'The two failed intermediate runs (closed-stream caller teardown and missing test parent directory) and all prior drafts remain retained. '
    'This unit used zero real native and zero Windows Jobs; the prior legacy-worker native-authority incident remains preserved and excluded.\n\n'
    f'Evidence: {check_path.relative_to(ROOT).as_posix()}, SHA256 {digest(check_path.read_bytes())}, {len(pins)} pins; '
    f'draft_state_25 SHA256 {digest(draft_path.read_bytes())}. '
    'All1042 closed predecessor pins and old v2/v3 outer895/1695 and run248/251 remain unchanged. '
    'This closes scoped PRE_SEAL development findings only; it is not an official verdict, canonical execution evidence or a run grant. '
    'Complete GroupRoster/common scientific correspondence, hour1+/192-hour integration, typed failed-Actual evidence, task/reuse DAG, '
    'same-contract LB/UB, full resource admission, successor sealing and a new official reviewer remain open. '
    'New real native still requires specific authorization for a concrete admitted package. All prior formal/resource/execution gates remain false.\n')
documents=[]
for path,raw in originals:
    assert path.read_bytes()==raw
    with path.open('ab') as stream:stream.write(addition.encode('utf-8'))
    updated=path.read_bytes();assert updated[:len(raw)]==raw
    documents.append(dict(path=path.relative_to(ROOT).as_posix(),before_sha256=digest(raw),after_sha256=digest(updated),original_bytes_preserved=True))
new(trace_path,dict(documents=documents,development_checks_sha256=digest(check_path.read_bytes()),draft_state_sha256=digest(draft_path.read_bytes())))
print(json.dumps(dict(pin_count=len(pins),root_tests=sum(expected.values()),independent_tests=sum(independent.values()),checks_sha256=digest(check_path.read_bytes()),draft_sha256=digest(draft_path.read_bytes()))))
