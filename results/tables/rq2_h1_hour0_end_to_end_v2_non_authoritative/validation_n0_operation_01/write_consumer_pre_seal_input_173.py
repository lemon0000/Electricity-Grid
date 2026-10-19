"""Bind current scoped evidence for a read-only non-authoritative audit."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import psutil

H=Path(__file__).resolve().parent;R=H.parents[3];D=H/'whole_workflow_optimization_01_non_authoritative'
results=[];paths={Path(__file__),H/'collect_consumer_evidence_172.py',D/'consumer_registry_read_scope_design_155.md',
    D/'consumer_registry_successors_draft_origin_156.json'}
for number in ('169','170','171'):
    path=D/('consumer_result_'+number+'.json');value=json.loads(path.read_bytes());results.append(value);paths.add(path)
    assert value['terminal']['exit_code']==0 and value['terminal']['source_unchanged'] and not value['pin_drift']
    assert value['terminal']['observed_owned_processes_absent'] and not value['terminal']['cleanup_errors']
    for proc in value['terminal']['observed_owned_processes']:
        try:assert abs(psutil.Process(proc['pid']).create_time()-proc['creation_time'])>1e-6
        except psutil.NoSuchProcess:pass
    for name,pin in value['source_sha256'].items():
        p=R/name;assert sha256(p.read_bytes()).hexdigest()==pin;paths.add(p)
    for row in value['archive_files']:
        p=Path(row['saved']);assert sha256(p.read_bytes()).hexdigest()==row['sha256'];paths.add(p)
for label in ('consumer_constructor_primary_units_169','bootstrap6_live_header_170','saved152_consumer_dag_171'):
    for name in ('request.json','started.json','terminal.json','stdout.log'):paths.add(H/label/name)
for name in ('saved152_numerical_postcheck_result_153.json','saved152_readonly_reopen_result_154.json',
    'bootstrap6_live_header_plan_170.json','saved152_consumer_dag_plan_171.json'):
    paths.add(D/name)
value=dict(schema='h1_consumer_pre_seal_input_173',status='PRE_SEAL_AUDIT_NONAUTHORITATIVE',
    at_utc=datetime.now(timezone.utc).isoformat(),root_sole_writer=True,risk='R3',
    request='Complete missing legacy postchecks without rerunning the body, then optimize the complete chain while preserving scientific/evidence boundaries.',
    scope='Bootstrap6/Owned6/Verifier5 consumer read scope and exact closed-record retirement; no Roster5 or genuine current N0 yet.',
    implementation=['One original guard and fresh nonce per constructor/inspect; two registry builds may share one confirmed proof only within that method.',
        'Original prepare/confirm/context/science algorithms unchanged. Empty reads are metadata observations, never numerical registration proofs.',
        'Close, detached immutable receipt, then exact record retirement. Global16-slot reservation includes active and pending; pending scopes retain private captured close retry.',
        'Creator close and closed-owner close retry all pending records; primary body error survives cleanup, nonce-clear and guard-release secondaries.',
        'Successful and failed diagnostic bytes share128 observation cap; no detached object is a consumer credential.'],
    accepted_pre_seal_findings=['P1 strong records retained completed scope/owner; add exact closed scope+operation retirement and owner GC tests.',
        'P2 preserve body primary through composite scope/receipt/retire/guard failures and save failed cleanup observations.',
        'P1 real partial retirement failure must preserve bounded original retry authority, including producer path; add two-arm pre-delete fault and sixteen pending-owner cap.',
        'P2 forbid any active capsule at retirement, including a foreign active value under same owner key.',
        'Constructor self.close failure must not mask read primary; exact handler and journal/phase/persistent-retire combination verified.'],
    acceptance=['Current150 targeted tests and source-preserving current genuine empty header lifecycle.',
        'Saved152 exact original audit and decision bytes, actual baseline/read-sized DAG counts and operation closure/retirement.',
        'Current source/plan/archive hashes match, observed PIDs absent, entry handles restored/closed and saved file set+bytes unchanged.',
        'Named findings only; do not issue an official verdict, receipt, production seal or formal-run authority.'],
    reused_evidence=['134 phase/coordinator faults on unchanged algorithm; current AST checks every unaffected Bootstrap function and scientific verifier function.',
        '151 original path entry failure scope; same entry6 exercised in170/171.',
        '153 saved152 original numerical oracle and154 external-head readonly reopen; no repeat of the original Job.'],
    open=['Actual Roster5 read/borrow/callback scope integration.',
        'Genuine current public N0 return/receipt/close with externally persisted heads.',
        'Three independent arms and typed Common/Genesis/Parent/Handoff/paired/Post/reopen.',
        'Complete whole-workflow performance/resource budget and separate formal readiness/authority.'],
    source_current=True,production_seal=False,official_review=False,review_receipt=False,
    full_optimized_workflow_accepted=False,whole_workflow_performance_review_complete=False,
    formal_execution_ready=False,formal_run_authority=False,formal_result=False,resource_admission=False,native_execution_authorized=False,
    files_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(paths,key=str)})
out=D/'consumer_pre_seal_input_173.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),pins=len(paths))))
