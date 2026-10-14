"""One-shot root evidence finalizer; no solver imports or execution authority."""
from pathlib import Path
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent

def pin(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_bytes())
def write(path,value):
    raw=(json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
    with path.open('xb') as stream:stream.write(raw)
    assert path.read_bytes()==raw
    return pin(path)

assert ROOT.name=='electricity-grid' and OUT.name.endswith('_non_authoritative')
previous=ROOT/'results/tables/rq2_h1_selector_launch_preparation_v1_non_authoritative/development_checks.json'
assert pin(previous)=='60819869aa53abd9a866abdab2fe8f0d2a83415c122dbe9eb5803c388103a8f5'
pins=dict(read(previous)['files_sha256'])
assert len(pins)==1036
assert all(pin(ROOT/name)==value for name,value in pins.items())
current={
    'experiments/h1_selector_parent_controller_development_v1.py':'e9084b6d5388b1c0be98753135d03a4c6d9340db7edf620abbc1e46257409826',
    'tests/test_h1_selector_parent_controller_development_v1.py':'36f6e74d6e0de57d3417732ff67ded52b695b5813d6bfb34df324d0ecb02de71',
    'docs/model_spec/rq2_h1_selector_parent_controller_development_v1.md':'e927df4fa97643fb966dec6613cc79f56ec9997f187edc74a023736a35587df6',
}
assert all(pin(ROOT/name)==value for name,value in current.items())
pins.update(current)
frozen=[]
for version in (2,3):
    outer=ROOT/f'configs/rq2_normal_h1_calibration_v{version}.OUTER.SHA256SUMS.json'
    members=read(outer)['members']
    assert len(members)==(895 if version==2 else 1695)
    assert all(pin(ROOT/name)==value for name,value in members.items())
    inventory=ROOT/f'results/tables/rq2_normal_h1_full_job_v{version}_non_authoritative/calibration_v{version}.postrun_inventory.json'
    doc=read(inventory);base=Path(doc['root'])
    assert len(doc['members'])==(248 if version==2 else 251)
    assert all(pin(base/name)==value['sha256'] and (base/name).stat().st_size==value['bytes'] for name,value in doc['members'].items())
    frozen.append(dict(version=version,outer_sha256=pin(outer),outer_members=len(members),
        inventory_sha256=pin(inventory),run_members=len(doc['members']),drift=[]))

review=read(OUT/'review_04.json')
assert review['reading_stopped'] and review['exit_code']==0 and not review['open_findings']
assert list(current.values())==[review['code_sha256'],review['test_sha256'],review['spec_sha256']]
base_command=['D:/Miniconda3/envs/compute/python.exe','-B','-m','pytest','-q','-p','no:cacheprovider']
test_file='tests/test_h1_selector_parent_controller_development_v1.py'
selected='borrowed or cleanup or scope or collision or canonical_parent'
parts=[]
for file,count,selection in [('root_scope_07.json',14,selected),('root_actual_08.json',1,'actual_requires'),
    ('root_remaining_09.json',26,'not ('+selected+' or actual_requires)')]:
    result=read(OUT/file)
    assert result['exit_code']==0
    found=re.search(r'(\d+) passed, (\d+) deselected in ([\d.]+)s',result['output'])
    assert found and int(found[1])==count and int(found[1])+int(found[2])==41
    parts.append(dict(command=base_command+[test_file,'-k',selection],passed=count,
        deselected=int(found[2]),pytest_seconds=float(found[3]),exit_code=0,evidence=file))
related=read(OUT/'root_related_10.json')
assert related['exit_code']==0
found=re.search(r'(\d+) passed in ([\d.]+)s',related['output'])
assert found and int(found[1])==72
related_record=dict(command=base_command+['tests/test_h1_selector_launch_preparation_development_v1.py',
    'tests/test_rq2_normal_resources_v1.py'],passed=72,pytest_seconds=float(found[2]),exit_code=0,evidence='root_related_10.json')

trace=read(previous.parent/'append_trace_01.json')
documents=[]
for row in trace['documents']:
    path=ROOT/row['path'];raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==row['after_sha256']
    documents.append((path,raw))
prior_state=read(ROOT/'results/tables/rq2_h1_bootstrap_integration_v1_non_authoritative/draft_state_21.json')
flags={key:value for key,value in prior_state.items() if type(value) is bool}
assert not any(flags.values())
flags.update(parent_phase_commit_verified=False,live_parent_completion_detached_replay=False)
evidence={p.relative_to(OUT).as_posix():pin(p) for p in sorted(OUT.rglob('*')) if p.is_file()}
scope='selector parent control flow and live-reference correspondence under synthetic lifecycle; canonical Job/native integration and phase consumption unresolved'
checks=dict(schema='h1_selector_parent_controller_checks_v1',status='PRE_SEAL_SCOPED_FINDINGS_CLOSED',scope=scope,
    previous_checks_path=previous.relative_to(ROOT).as_posix(),previous_checks_sha256=pin(previous),
    pin_count=len(pins),files_sha256=pins,evidence_files_sha256=evidence,frozen_verification=frozen,
    root_partition_tests=parts,root_partition_total_passed=41,root_partition_disjoint_complete=True,
    safe_related_test=related_record,independent_review='review_04.json',findings_closed=review['findings_closed'],
    synthetic_parent_control_flow_verified=True,canonical_parent_completion_verified=False,
    canonical_worker_success_verified=False,canonical_job_success_verified=False,
    unit_real_native_calls=0,unit_windows_jobs=0,formal_runs=0,
    historical_authority_incident=prior_state['authority_boundary_incident'],incident_counted_as_unit_evidence=False,
    **flags)
checks_path=OUT/'development_checks.json';checks_pin=write(checks_path,checks)
state_path=ROOT/'results/tables/rq2_h1_bootstrap_integration_v1_non_authoritative/draft_state_22.json'
state_pin=write(state_path,dict(status='DRAFT_NONAUTHORITATIVE',scope=scope,
    development_checks_path=str(checks_path),development_checks_sha256=checks_pin,
    authority_boundary_incident=prior_state['authority_boundary_incident'],**flags))
paragraph=f'''

### 2026-10-12 - Selector parent controller scoped development reviewed

Added experiments/h1_selector_parent_controller_development_v1.py with tests and spec. The parent persists its binding before worker inputs, retains bounded create-once transport, writes initial/child/release records before release, invokes fresh output inspection only at the lifecycle quiescence callback, and jointly binds observation/diagnostic in a parent terminal before issuing an exact live completion. Actual retains the Rref operation lock and fresh completion correspondence through execution and replay. Source provenance uses a conservative exact common-view/global-head restriction; general journal ancestry remains open.

PRE_SEAL F1-F7 are closed: scientific request keys are separate from timed-sequence keys and recomputed into terminal/replay; original scope checks are closure-anchored at exact-owner public entrypoints; nonce collisions cannot replace an owner; synthetic lifecycle identity is distinct; borrowed methods reject foreign self before effects; failure cleanup captures original dependencies and verifies exact registry ownership before touching a lease. Tests cover copied shared-lease attacks, callback-time replacement, constructor/run write before/after failures, completion identity/thread/lifetime, callback order/return mismatch, Actual failure lock release, and same-byte archive replacement.

Root final-byte tests partition all41 cases without overlap:14 targeted,1 Rref-to-Actual lifetime scenario,26 remaining; all exit0. Related unchanged launch-preparation/resources72 passed, exit0. Independent14 passed/27 deselected in88.32s, exit0, unchanged hashes. Earlier failures and the two root-interrupted synthetic suites are preserved and are not passing evidence. This unit uses zero real native and zero Windows Jobs; fabricated in-process worker/lifecycle tests do not prove canonical Job/native success. The previously documented legacy-worker native-authority incident remains preserved and excluded.

Evidence: {checks_path.relative_to(ROOT).as_posix()}, SHA256 {checks_pin},1039 pins. All1036 predecessor pins and historical v2/v3 outer895/1695 and run248/251 are unchanged. Draft state22 SHA256 {state_pin}. This is scoped PRE_SEAL closure only, not official review or authority. All formal/resource/native/phase-consumption flags remain false.

Next connect persistent common-phase consumption to the owned selector parent completion and paired transaction. Canonical source/Job execution evidence, N-to-Rref-to-business/Actual paired commit, hour1+/192-hour producer coverage, actual task/reuse DAG, common-contract LB/UB, full resource admission, successor sealing and a fresh official reviewer remain open. New real native still requires a concrete admitted package and separate specific authorization. selector_parent_connected=false; owner_consumption_authorized=false; parent_phase_commit_verified=false; non_solver_allowance_verified=false; resource_admission=false; formal_execution_ready=false; formal_result=false; native_execution_authorized=false.
'''.encode('utf-8')
appended=[]
for path,raw in documents:
    assert path.read_bytes()==raw
    with path.open('ab') as stream:stream.write(paragraph)
    assert path.read_bytes()==raw+paragraph
    appended.append(dict(path=path.relative_to(ROOT).as_posix(),before_sha256=hashlib.sha256(raw).hexdigest(),
        after_sha256=pin(path),original_bytes_preserved=True))
write(OUT/'append_trace_01.json',dict(documents=appended,development_checks_sha256=checks_pin,draft_state_sha256=state_pin))
print(json.dumps(dict(checks_sha256=checks_pin,draft_sha256=state_pin,pins=len(pins),evidence_files=len(evidence))))
