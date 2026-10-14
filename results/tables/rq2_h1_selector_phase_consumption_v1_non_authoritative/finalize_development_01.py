"""One-shot root-only scoped preview evidence; no solver imports or authority."""
from pathlib import Path
import hashlib
import json

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
previous=ROOT/'results/tables/rq2_h1_selector_parent_controller_v1_non_authoritative/development_checks.json'
assert pin(previous)=='5187fbea39f6fccf39346f5718fc769b3da9e30f94da14244b160e86ae0fb017'
pins=dict(read(previous)['files_sha256'])
assert len(pins)==1039 and all(pin(ROOT/name)==value for name,value in pins.items())
current={
    'experiments/h1_selector_phase_consumption_development_v1.py':'708d75a2f5762f26be67074143e91e62a566d0f3c6e1fc2f2c9dd8eaec44e919',
    'tests/test_h1_selector_phase_consumption_development_v1.py':'1668683b2c2419dc1b14b4221dc0fa321d322ac6ae97ae907a2e03d4f8c0bd95',
    'docs/model_spec/rq2_h1_selector_phase_consumption_development_v1.md':'3965623c256e04de14c7daebf30137dec05206f010aa3f95e58afe9fed7fe10c',
}
assert all(pin(ROOT/name)==value for name,value in current.items())
pins.update(current)
frozen=[]
for version in (2,3):
    outer=ROOT/f'configs/rq2_normal_h1_calibration_v{version}.OUTER.SHA256SUMS.json'
    members=read(outer)['members']
    assert len(members)=={2:895,3:1695}[version]
    assert all(pin(ROOT/name)==value for name,value in members.items())
    inventory=ROOT/f'results/tables/rq2_normal_h1_full_job_v{version}_non_authoritative/calibration_v{version}.postrun_inventory.json'
    doc=read(inventory);base=Path(doc['root'])
    assert len(doc['members'])=={2:248,3:251}[version]
    assert all(pin(base/name)==value['sha256'] and (base/name).stat().st_size==value['bytes'] for name,value in doc['members'].items())
    frozen.append(dict(version=version,outer_sha256=pin(outer),outer_members=len(members),
        inventory_sha256=pin(inventory),run_members=len(doc['members']),drift=[]))

review=read(OUT/'review_02.json');tests=read(OUT/'root_tests_04.json');related=read(OUT/'root_related_03.json')
assert review['reading_stopped'] and review['exit_code']==0 and not review['open_findings']
assert list(current.values())==[review['code_sha256'],review['test_sha256'],review['spec_sha256']]
assert tests['exit_code']==related['exit_code']==0 and tests['passed']==related['passed']==18
assert tests['files_sha256']==current
documents=[]
for row in read(previous.parent/'append_trace_01.json')['documents']:
    path=ROOT/row['path'];raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==row['after_sha256']
    documents.append((path,raw))
prior_state=read(ROOT/'results/tables/rq2_h1_bootstrap_integration_v1_non_authoritative/draft_state_22.json')
flags={key:value for key,value in prior_state.items() if type(value) is bool}
assert not any(flags.values())
scope='pure hour-0 bootstrap ticket preview and supplied-prefix failure observation; live Parent/common handoff and paired consumption not implemented'
evidence={p.relative_to(OUT).as_posix():pin(p) for p in sorted(OUT.rglob('*')) if p.is_file()}
checks=dict(schema='h1_selector_phase_consumption_checks_v1',status='PRE_SEAL_PREVIEW_SCOPED_FINDINGS_CLOSED',scope=scope,
    previous_checks_path=previous.relative_to(ROOT).as_posix(),previous_checks_sha256=pin(previous),
    pin_count=len(pins),files_sha256=pins,evidence_files_sha256=evidence,frozen_verification=frozen,
    root_test=tests,related_test=related,independent_review='review_02.json',findings_closed=review['findings_closed'],
    preview_matches_synthetic_phase_persistence=True,constructible_plan_is_credential=False,
    observation_reads_live_storage=False,live_handoff_implemented=False,controller_journal_implemented=False,
    unit_real_native_calls=0,unit_windows_jobs=0,formal_runs=0,
    historical_authority_incident=prior_state['authority_boundary_incident'],incident_counted_as_unit_evidence=False,**flags)
checks_path=OUT/'development_checks.json';checks_pin=write(checks_path,checks)
state_pin=write(ROOT/'results/tables/rq2_h1_bootstrap_integration_v1_non_authoritative/draft_state_23.json',
    dict(status='DRAFT_NONAUTHORITATIVE',scope=scope,development_checks_path=str(checks_path),
        development_checks_sha256=checks_pin,authority_boundary_incident=prior_state['authority_boundary_incident'],**flags))
paragraph=f'''

### 2026-10-12 - Selector phase ticket preview and failure observation reviewed

Added experiments/h1_selector_phase_consumption_development_v1.py with tests and spec. Implemented scope is a PURE bootstrap preview and supplied-prefix observer, not the live phase consumer. The preview preserves full raw records, the complete lane roster, both exact phase tickets, holder record bytes and prospective heads, and the existing full three-event branch reservation. Seven legal retained-head/holder/DB prefix shapes distinguish planned-only, retention pending, DB commit pending, outcome pending and complete rows. Unknown suffixes and impossible orders reject; complete rows do not authenticate a controller terminal or parent execution. Constructible plans do not establish Actual failure.

Root final18 passed45.05s, related existing phase-owner18 passed116.33s, all exit0. Independent first14 passed33.59s, then4 passed/14 deselected17.84s after two test findings were fixed, all exit0 with unchanged reviewed hashes. Evidence includes ten write-failure windows, two-lane commit/freeze correspondence, missing/extra roster keys, exact branch and body limits, and a conservative holder-byte bound. Unit tests use fabricated records and a synthetic source seam: zero real native and zero Windows Jobs. The earlier legacy-worker native-authority incident remains preserved and excluded from scientific/admission evidence.

Evidence: {checks_path.relative_to(ROOT).as_posix()}, SHA256 {checks_pin},1042 pins. All1039 predecessor pins and historical v2/v3 outer895/1695 and run248/251 remain unchanged. Draft state23 SHA256 {state_pin}. This is scoped PRE_SEAL preview closure only, not official review or an implemented paired consumer.

Independent design requirements remain in design_review_01.json: exact Parent bundle guards through fresh archive replay and final readback; common/roster guards through genesis handoff with fixed child roots/headers; complete takeover intent plus each holder_head_prepared event externally retained inside its callback; preflight full journal capacity; typed complete lane dispositions. Missing or failed started Actual work stays pending until typed failure evidence exists. No speculative head adoption, outcome retry, or automatic recovery is authorized. Preserve all proof-terminal/joint-B6 obligations. Live consumption, hour1+/192-hour coverage, actual task/reuse DAG, common-contract LB/UB, full resource admission, successor seal and new official review remain open. All prior formal/resource/native/phase-consumption gates remain false; specific new native authority is still required for a concrete admitted package.
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
