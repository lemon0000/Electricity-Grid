"""Preserve reviewed draft bytes and scoped findings before further integration."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import psutil

H=Path(__file__).resolve().parent;R=H.parents[3];D=H/'whole_workflow_optimization_01_non_authoritative'
sources=[
    'experiments/h1_bootstrap_integration_development_v7.py',
    'experiments/h1_owned_bootstrap_controller_development_v7.py',
    'experiments/h1_historical_n0_verifier_development_v6.py',
    'experiments/h1_group_execution_roster_development_v5.py',
    'experiments/h1_phase_dependency_validation_operation_development_v2.py',
    'experiments/h1_phase_manifest_binding_development_v4.py',
    'experiments/h1_phase_manifest_validation_operation_development_v2.py',
    'experiments/h1_group_n0_common_input_binding_development_v9.py',
    'experiments/h1_group_n0_common_input_binding_development_v10.py',
    'tests/test_h1_registry_validation_operation_development_v6.py',
    'tests/test_h1_consumer_registry_read_development_v7.py',
    'tests/test_h1_roster_registry_binding_development_v5.py',
    'tests/test_h1_roster_registry_read_development_v5.py',
    'tests/test_h1_roster5_live_header_development_v1.py',
    'tests/test_h1_phase_dependency_validation_operation_development_v2.py',
    'tests/test_h1_phase_dependency_window_faults_development_v2.py',
    'tests/test_h1_phase_manifest_binding_development_v4.py',
    'tests/test_h1_phase_manifest_validation_operation_development_v2.py']
evidence=[]
for number in ('199','200','201'):
    path=D/('roster_result_'+number+'.json');v=json.loads(path.read_bytes())
    assert v['terminal']['exit_code']==0 and v['terminal']['source_unchanged']
    for row in v['archive_files']:
        assert sha256(Path(row['saved']).read_bytes()).hexdigest()==row['sha256']
    for row in v['terminal']['observed_owned_processes']:
        try:assert abs(psutil.Process(row['pid']).create_time()-row['creation_time'])>1e-6
        except psutil.NoSuchProcess:pass
    evidence.append(dict(path=str(path.relative_to(R)),sha256=sha256(path.read_bytes()).hexdigest(),
        cases=v['pytest_cases'],outer_seconds=v['terminal']['elapsed_seconds']))
archive=D/'roster_scoped_source_202_non_authoritative';archive.mkdir(exist_ok=False)
snapshots=[]
for name in sources:
    source=R/name;target=archive/source.name;raw=source.read_bytes()
    with target.open('xb') as stream:stream.write(raw)
    assert target.read_bytes()==source.read_bytes()
    snapshots.append(dict(source=name,saved=str(target.relative_to(R)),sha256=sha256(raw).hexdigest()))
value=dict(schema='h1_roster_scoped_findings_202',status='PRE_SEAL_NAMED_FINDINGS_CLOSED_NONAUTHORITATIVE',
    at_utc=datetime.now(timezone.utc).isoformat(),root_sole_writer=True,risk='R3',
    reviewer='/root/public_phase_review_118',evidence=evidence,source_snapshots=snapshots,
    findings=[dict(name='same-code caller/body/invocation clones',resolution='Exact wrapper, invoke and first body frames; one-shot invocation, fixed CALLsites and creator-owned private phase stack.'),
        dict(name='active callback scope reentry',resolution='Callbacks occur with no scope/producer nonce; callback-active guard rejects all nonconstructor phase routes and scope openings.'),
        dict(name='scope cleanup and resource accounting',resolution='Shared lock covers reserve/attach/snapshot/forget; sixteen live-or-pending slots, original close/retire retry, detached bounded descriptions, primary preserved.'),
        dict(name='definition-time Common dependency TOFU',resolution='All Common registration explicitly denied at these bytes; authenticated integration remains open.')],
    verified=['36 current caller/frame/callback/protocol regression cases',
        'Genuine empty create/inspect/close/reopen: eight phase windows and ten distinct empty registry scopes',
        'Seven real phase canonical science/manifest/audit byte and failed-segment regressions',
        'Actual archive SHA readback, source pins, observed PID absence and original handles closed'],
    trust_boundary='Private closure and frame state is trusted against direct mutation; read/clone adversaries covered by named negatives. No native/ctypes frame forgery or security certification.',
    open=['Genuine numeric Roster and three independent N0s','Pinned typed Common/Genesis/Handoff graph and loader lifecycle',
        'Common exact private provisional rows and per-replay parent/callsite/ticket binding',
        'Whole optimized chain, complete performance/resource budget and separate formal gates'],
    complete_process_tree_absence_proven=False,storage_path_ABA_covered=False,
    production_seal=False,official_review=False,review_receipt=False,formal_run_authority=False,
    full_optimized_workflow_accepted=False,whole_workflow_performance_review_complete=False,
    formal_execution_ready=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
out=D/'roster_scoped_findings_202.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),source_snapshots=len(snapshots))))
