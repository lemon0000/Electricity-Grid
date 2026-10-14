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
independent={'independent_tests_35.json':6,'independent_global_29.json':2,
             'independent_resources_30.json':25,'independent_real_roster_32.json':2}
tests={}
for name,count in (expected|independent).items():
    result=read(HERE/name)
    assert result['exit_code']==0,(name,result['output'])
    assert result['real_native_calls']==0 and result['windows_jobs']==0
    assert int(re.search(r'(\d+) passed',result['output']).group(1))==count
    assert result['before']==result['after']
    assert all(digest((ROOT/p).read_bytes())==pin for p,pin in result['after'].items())
    tests[name]=dict(passed=count,exit_code=0,output=result['output'])
review=read(HERE/'preseal_closure_33.json')
assert review['schema']=='h1_selector_phase_handoff_preseal_review_v1'
assert review['reviewer']=='/root/selector_owner_design_review' and review['reading_stopped'] is True
assert review['scoped_development_findings_closed'] is True and review['official_verdict'] is False
assert review['real_native_calls']==0 and review['windows_jobs']==0
assert review['root_tests_passed']==sum(expected.values()) and review['independent_tests_passed']==sum(independent.values())
assert review['evidence_files_sha256']=={name:digest((HERE/name).read_bytes()) for name in (expected|independent)}
assert review['finalizer_sha256']==digest(Path(__file__).read_bytes())
assert all(digest((ROOT/p).read_bytes())==pin for p,pin in review['files_sha256'].items())
previous=ROOT/'results/tables/rq2_h1_selector_phase_consumption_v1_non_authoritative/development_checks.json'
assert digest(previous.read_bytes())=='560797ad578f2f5b0c0cb186f877158e9e3ca1c0dd41c398a9270cdf72814268'
old=read(previous)
files=['experiments/h1_selector_phase_handoff_development_v1.py',
       'docs/model_spec/rq2_h1_selector_phase_handoff_development_v1.md']
files += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'tests').glob('test_h1_selector_phase_handoff*_development_v1.py'))]
pins=old['files_sha256']|{p:digest((ROOT/p).read_bytes()) for p in files}
assert len(old['files_sha256'])==1042
assert review['files_sha256']=={p:pins[p] for p in files}
assert all(digest((ROOT/p).read_bytes())==pin for p,pin in pins.items())
anchors=dict(predecessor_pins=1042,drift=[],
    v2_outer=dict(sha256='79830ab6c1b31aaef41174544e472ef800674de1f76228793f30f6b87e4f6eba',members=895),
    v3_outer=dict(sha256='e3acc7a6de1c1863ab64a8c1ae67ded9676e01c564a3d4ef2d0be29252f0edcf',members=1695),
    v2_run=dict(sha256='281ad90c2da8bdb2ff0a1031d94379f2887dc663f235c52619a1c75e25521fb4',members=248),
    v3_run=dict(sha256='e80dacf5c44b39ad71ff29dce980d3e03cee6f4bf9fad6d3be620061e171d596',members=251))
assert read(HERE/'predecessor_verification_22.json')==anchors
for version in (2,3):
    outer=ROOT/f'configs/rq2_normal_h1_calibration_v{version}.OUTER.SHA256SUMS.json'
    inventory=ROOT/f'results/tables/rq2_normal_h1_full_job_v{version}_non_authoritative/calibration_v{version}.postrun_inventory.json'
    for kind,path in (('outer',outer),('run',inventory)):
        anchor=anchors[f'v{version}_{kind}'];value=read(path)
        assert digest(path.read_bytes())==anchor['sha256'] and len(value['members'])==anchor['members']
        for name,pin in value['members'].items():
            if kind=='outer':assert digest((ROOT/name).read_bytes())==pin
            else:
                raw=(Path(value['root'])/name).read_bytes()
                assert digest(raw)==pin['sha256'] and len(raw)==pin['bytes']
prior=read(HERE/'append_trace_01.json');originals=[]
assert len(prior['documents'])==2
# Resolve only fixed destinations and hashes. UTF-8 JSON readback confirms the
# historical path is correct even when a terminal renders its text incorrectly.
destinations=[('docs/plan/科研项目执行步骤.md','83c9c5c150f9a4bb220f5b332b95d4208233f545befc53400ffc6a75522d78b2'),
              ('docs/model_spec/blocker_register.md','05283de4cfb27bde68254b71bcbb70bf533a6f9fe770c9a9e088b662c164f29a')]
for item,(relative,expected_hash) in zip(prior['documents'],destinations):
    assert item['after_sha256']==expected_hash
    path=ROOT/relative;raw=path.read_bytes()
    assert digest(raw)==item['after_sha256']
    originals.append((path,raw))
prior_draft=ROOT/'results/tables/rq2_h1_bootstrap_integration_v1_non_authoritative/draft_state_24.json'
assert digest(prior_draft.read_bytes())=='aa700a16dd8c1e3d92356e872b1c3b95e3a022b929c53be39daba7cd7a082744'
flags={k:v for k,v in read(prior_draft).items() if type(v) is bool}
assert flags and all(value is False for value in flags.values())
incident_path=ROOT/'results/tables/rq2_h1_selector_launch_preparation_v1_non_authoritative/native_boundary_incident_01/incident.json'
incident_pin='c88003fe228723a50616ff3c41371cc01ee75069f61ee7b6203f20fffdd9ae1a'
assert digest(incident_path.read_bytes())==incident_pin
incident=read(incident_path)
assert incident['confirmed_persisted_native_calls']==3 and incident['preserved_file_count']==109
assert incident['total_native_call_count_complete'] is False
assert incident['formal_run'] is False and incident['run_authorized'] is False
incident_inventory_path=incident_path.parent/'inventory.json'
incident_inventory_pin='060b0bef69c4a480dbae6262987984b3bfa06bc1755f1246676b1d6011a2cdc1'
assert digest(incident_inventory_path.read_bytes())==incident_inventory_pin
incident_inventory=read(incident_inventory_path)
assert incident_inventory['file_count']==len(incident_inventory['files_sha256'])==109
for name,pin in incident_inventory['files_sha256'].items():
    assert digest((incident_path.parent/name).read_bytes())==pin
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
    historical_authority_incident=incident_path.relative_to(ROOT).as_posix(),
    historical_authority_incident_sha256=incident_pin,historical_incident_inventory_sha256=incident_inventory_pin,
    historical_incident_inventory_path=incident_inventory_path.relative_to(ROOT).as_posix(),
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
    'The two failed intermediate test runs (closed-stream caller teardown and missing test parent directory), '
    'the superseded independent snapshot and its rejected current-pin verification, and all prior drafts remain retained. '
    'This unit used zero real native and zero Windows Jobs; the prior legacy-worker native-authority incident remains preserved and excluded.\n\n'
    f'Evidence: {check_path.relative_to(ROOT).as_posix()}, SHA256 {digest(check_path.read_bytes())}, {len(pins)} pins; '
    f'draft_state_25 SHA256 {digest(draft_path.read_bytes())}. '
    'All 1042 closed predecessor pins and old v2/v3 outer895/1695 and run248/251 remain unchanged. '
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
new(trace_path,dict(documents=documents,historical_trace_sha256=digest((HERE/'append_trace_01.json').read_bytes()),
    historical_path_text_preserved=[item['path'] for item in prior['documents']],
    development_checks_sha256=digest(check_path.read_bytes()),draft_state_sha256=digest(draft_path.read_bytes())))
print(json.dumps(dict(pin_count=len(pins),root_tests=sum(expected.values()),independent_tests=sum(independent.values()),checks_sha256=digest(check_path.read_bytes()),draft_sha256=digest(draft_path.read_bytes()))))
