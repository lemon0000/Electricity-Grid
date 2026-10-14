"""Root-only create-once development records, never formal authority."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

p=Path(__file__).parent
def sha(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
def read(f):return json.loads(Path(f).read_text(encoding='utf-8'))
def write(f,value):
    with Path(f).open('x',encoding='utf-8') as out:json.dump(value,out,indent=2,ensure_ascii=False)

pins_now=read(p/'before_test_03.json')
assert all(sha(f)==h for f,h in pins_now.items())
review=read(p/'independent_review_02.json')
assert review['status']=='PRE_SEAL_SCOPED_FINDINGS_CLOSED' and review['reading_stopped']
assert review['reviewed_hashes']==pins_now
assert review['independent_test']['exit_code']==0 and review['independent_test']['files_unchanged']
tests={}
for stem,count in [('root_test_03',35),('root_regression_01',74)]:
    report=read(p/(stem+'.json'))
    assert report['exit_code']==0 and report['files_unchanged']
    match=re.search(r'(\d+) passed in ([0-9.]+)s',(p/(stem+'.log')).read_text(encoding='utf-8'))
    assert match and (count is None or int(match[1])==count)
    tests[stem]=dict(report,passed=int(match[1]),pytest_seconds=float(match[2]))

old=Path('results/tables/rq2_h1_owned_selector_sequence_v1_non_authoritative/development_checks.json')
assert sha(old)=='9cf62aff9539504705449c6b407b4e431692c3c83de5b2bdecebb9b9b0f4abe6'
pins=dict(read(old)['files_sha256']);assert len(pins)==1014
assert all(sha(f)==h for f,h in pins.items())
pins.update(pins_now);assert len(pins)==1017
frozen={}
for v,outer_pin,nouter,nrun in [
    (2,'79830ab6c1b31aaef41174544e472ef800674de1f76228793f30f6b87e4f6eba',895,248),
    (3,'e3acc7a6de1c1863ab64a8c1ae67ded9676e01c564a3d4ef2d0be29252f0edcf',1695,251)]:
    outer=Path(f'configs/rq2_normal_h1_calibration_v{v}.OUTER.SHA256SUMS.json')
    members=read(outer)['members'];assert sha(outer)==outer_pin and len(members)==nouter
    assert all(sha(f)==h for f,h in members.items())
    inventory=read(f'results/tables/rq2_normal_h1_full_job_v{v}_non_authoritative/calibration_v{v}.postrun_inventory.json')
    assert len(inventory['members'])==nrun
    for f,item in inventory['members'].items():
        path=Path(inventory['root'])/f
        assert sha(path)==item['sha256'] and path.stat().st_size==item['bytes']
    frozen[str(v)]=dict(outer_sha256=outer_pin,member_count=nouter,member_drift=[],run_count=nrun,run_drift=[])
assembly=read('results/tables/rq2_h1_bootstrap_phase_manifest_binding_v1_non_authoritative/development_checks.json')['reviewed_open_assembly']
assert all(sha(f)==v['sha256']==sha(v['snapshot']) for f,v in assembly.items())
trace=read(old.parent/'append_trace_01.json')
assert all(sha(v['path'])==v['after_sha256'] for v in trace['documents'])
evidence={f.name:sha(f) for f in sorted(p.iterdir()) if f.is_file()}
gates=dict(whole_bootstrap_closed=False,persistent_common_owner_bound=False,group_execution_ready=False,
    common_reference_input_verified=False,selector_producer_connected=False,paired_owner_authenticated=False,
    N_reuse_verified=False,Rref_reuse_verified=False,resource_admission=False,formal_execution_ready=False,
    formal_result=False,native_execution_authorized=False,official_verdict=False,continuation_ready=False,
    owner_consumption_authorized=False,whole_job_quiescence_checked=False)
write(p/'development_checks.json',dict(schema='h1_selector_input_snapshot_checks_v1',
    status='PRE_SEAL_SCOPED_FINDINGS_CLOSED',scope='hour-zero reference and actual source-rebuilt input snapshots',
    previous_checks_path=old.as_posix(),previous_checks_sha256=sha(old),pin_count=len(pins),files_sha256=pins,
    evidence_sha256=evidence,root_tests=tests,independent_test=review['independent_test'],
    regression_scope='unchanged common-owner genesis and complete selector sequence; separate process',
    fabricated_direct_adapter=True,real_reference_capture_and_exact_business_mapping_tested=True,
    actual_RTS_group_integration_verified=False,full_192_hour_execution_verified=False,
    native_calls=0,research_jobs=0,**gates))
checks_sha=sha(p/'development_checks.json')
ind=review['independent_test']
summary=f'''

### 2026-10-11 - Hour-zero selector input reconstruction development reviewed

The standalone selector snapshot captures fixed declarations under the exact live common-genesis guards, requires its complete binder and empty holder/owner receipts, and bookends common/source/configuration correspondence. Detached rebuild performs two fresh source and initial-state reconstructions. It verifies complete typed Manifest/SourceBinding/SelectorRunConfiguration correspondence and exact network/UID/stage/selector/archive declaration. No serialized physical or business carry is accepted.

Actual snapshots can only be prepared after the complete Rref sequence exists. Both rebuild rounds inspect that archive against the same source and reference before-state, derive exact g=B-P_ref, run the unchanged business mapping and construct exact Actual power for that lane. The request API has no caller-supplied power field. Unresolved business rules or missing/incomplete/mismatched Rref remain unresolved. The detached object is constructible diagnostic evidence, not a live owner or Job capability; its genesis receipts record capture provenance rather than current owner-file authentication.

PRE_SEAL F1 binds the complete canonical declaration SHA separately from scientific identity, including accounting/capacity labels and archive caps. F2 requires exact canonical absolute common roots. The initial root failure (25 passed/1 failed) exposed the omitted full declaration binding and is retained with original snapshots and review findings. Final root suite: {tests['root_test_03']['passed']} passed in {tests['root_test_03']['pytest_seconds']}s; related common-owner/sequence regression: {tests['root_regression_01']['passed']} passed in {tests['root_regression_01']['pytest_seconds']}s; independent targeted: {ind['passed']} passed/{ind['deselected']} deselected in {ind['pytest_seconds']}s. All final checks exit0, fixed bytes unchanged. Tests cover declaration changes, noncanonical roots, source/global/guard/configuration bookends, exact g=59/4 and Actual power=21/4 Fraction oracle, actual business unresolved, and incomplete/tampered reference evidence. Synthetic source/roster seams and fabricated direct adapters do not prove actual RTS integration or native optimality.

Evidence: {p.as_posix()}/development_checks.json, SHA256 {checks_sha}, 1017 pins. All predecessor pins, open bootstrap snapshots, v2/v3 outer895/1695 and run248/251 remain unchanged. Zero native and zero research Job. This is scoped PRE_SEAL development closure only; no official verdict or execution authority.

Next connect the owned released worker and selector Windows Job controller, retain launch/release/child/clock/budget/quiescence evidence, then fresh parent inspection and common phase transaction consumption. Snapshot rebuild alone does not establish past native execution or current live ownership. Hour1+ requires independent read-only phase-prefix reconstruction; full192 producer/resource coverage, B6/other-family obligations, verified reuse DAG, same-contract LB/UB, successor seal and fresh official review remain open. owner_consumption_authorized=false; selector_producer_connected=false; continuation_ready=false; resource_admission=false; formal_execution_ready=false; formal_result=false; native_execution_authorized=false. New native execution requires concrete gates and separate explicit authority.
'''.encode('utf-8')
updates=[]
for item in trace['documents']:
    target=Path(item['path']);before=target.read_bytes()
    assert sha(target)==item['after_sha256']
    with target.open('ab') as out:out.write(summary)
    assert target.read_bytes()==before+summary
    updates.append(dict(path=target.as_posix(),before_sha256=item['after_sha256'],after_sha256=sha(target),original_bytes_preserved=True))
write(p/'append_trace_01.json',dict(documents=updates,development_checks_sha256=checks_sha))
draft=Path('results/tables/rq2_h1_bootstrap_integration_v1_non_authoritative/draft_state_15.json')
write(draft,dict(status='DRAFT_NONAUTHORITATIVE',scope='hour-zero selector input snapshot development closure',
    development_checks_path=(p/'development_checks.json').as_posix(),development_checks_sha256=checks_sha,**gates))
diff=subprocess.run(['git','diff','--check'],capture_output=True,text=True)
assert diff.returncode==0,diff.stdout+diff.stderr
status=subprocess.check_output(['git','status','--short'],text=True)
assert all(sha(f)==h for f,h in pins.items())
write(p/'final_verification_01.json',dict(development_checks_sha256=checks_sha,pin_count=len(pins),pin_drift=[],
    evidence_count=len(evidence),evidence_drift=[f for f,h in evidence.items() if sha(p/f)!=h],frozen=frozen,
    open_assembly_drift=[],document_hashes_match=True,draft_state_path=draft.as_posix(),draft_state_sha256=sha(draft),
    git_diff_check_exit=diff.returncode,git_status_count=len(status.splitlines())))
print(json.dumps(dict(development_checks_sha256=checks_sha,pin_count=len(pins),draft_state_sha256=sha(draft))))
