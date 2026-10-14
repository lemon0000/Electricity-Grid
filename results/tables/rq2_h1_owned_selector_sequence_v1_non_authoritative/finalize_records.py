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
for stem,count in [('root_test_03',43),('root_regression_01',None)]:
    report=read(p/(stem+'.json'))
    assert report['exit_code']==0 and report['files_unchanged']
    match=re.search(r'(\d+) passed in ([0-9.]+)s',(p/(stem+'.log')).read_text(encoding='utf-8'))
    assert match and (count is None or int(match[1])==count)
    tests[stem]=dict(report,passed=int(match[1]),pytest_seconds=float(match[2]))

old=Path('results/tables/rq2_h1_common_owner_genesis_v1_non_authoritative/development_checks.json')
assert sha(old)=='0c9df634979e0b0811e4e1222bd7f18ee9173e61548f1791daddcebc8d5f9fa6'
pins=dict(read(old)['files_sha256']);assert len(pins)==1011
assert all(sha(f)==h for f,h in pins.items())
pins.update(pins_now);assert len(pins)==1014
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
write(p/'development_checks.json',dict(schema='h1_owned_selector_sequence_checks_v1',
    status='PRE_SEAL_SCOPED_FINDINGS_CLOSED',scope='complete one-shot selector capture chain and detached full-prefix inspector',
    previous_checks_path=old.as_posix(),previous_checks_sha256=sha(old),pin_count=len(pins),files_sha256=pins,
    evidence_sha256=evidence,root_tests=tests,independent_test=review['independent_test'],
    regression_scope='unchanged single-stage capture, inspector and run-configuration dependencies; separate process',
    fabricated_direct_adapter=True,real_full_selector_capture_replay_tested=True,
    actual_RTS_group_integration_verified=False,full_192_hour_execution_verified=False,
    native_calls=0,research_jobs=0,**gates))
checks_sha=sha(p/'development_checks.json')
ind=review['independent_test']
summary=f'''

### 2026-10-11 - Complete owned selector sequence development reviewed

The new standalone sequence binds the full typed SelectorRunConfiguration, exact normal-network identity and sorted generation UID inventory, lane, before-state/policy, disclosure input and prescribed Actual power. Each stage runs the closed raw-before-audit bridge, then independently reconstructs its record and canonical lock. Prefix-linked commits include the exact prior record vector, request, stage terminal, record, lock and completion bit. Before each subsequent stage release, saved prefix bytes, the original runner/reader/guard, inputs and nonce are rechecked. Final saved replay must reconstruct the complete selector candidate before the sequence terminal/private live completion can be returned. Detached inspection does not recreate an owned execution capability.

PRE_SEAL F1 required exact equality with the configured full stage order; F2 added the final live/prefix bookend immediately before stage release. Both are closed. Root final suite: 43 passed in {tests['root_test_03']['pytest_seconds']}s; related raw bridge/inspector/configuration suites: {tests['root_regression_01']['passed']} passed in {tests['root_regression_01']['pytest_seconds']}s; independent targeted: {ind['passed']} passed/{ind['deselected']} deselected in {ind['pytest_seconds']}s. All exit0 and reviewed bytes unchanged. Coverage includes both roles, all UIDs including a disabled second generator, stage-order shortening/reordering, callback identity changes, second-stage failures, prior raw/commit drift, exact fourteen-file logical payload bounds, unknown suffixes and live receipt mutation. All solver outputs use fabricated direct adapters; no actual RTS execution or native optimality is inferred.

The initial multi-UID fixture failure (13 passed/1 failed) remains recorded. Disabled G2 was corrected to disabled dispatch mode, zero current bounds and zero noncommittable state age, matching the unchanged source contract. All earlier drafts, review findings, failed logs and snapshots remain. The logical payload cap excludes filesystem allocation overhead, scratch, RAM and host reserve and is not resource admission.

Evidence: {p.as_posix()}/development_checks.json, SHA256 {checks_sha}, 1014 pins. All predecessor pins, open-bootstrap reviewed snapshots, v2/v3 outer895/1695 and old run248/251 are retained without drift. Zero real native and zero research Job. This is scoped PRE_SEAL development closure, not an official verdict or run authority.

Next implement the owned selector worker transport and Windows Job controller with complete release/child/clock/budget/quiescence evidence, then internally connect Rref replay, exact business mapping, independent Actual lanes and paired phase commit. Complete192 coverage, hour1+ continuation, B6/other-family obligations, same-contract LB/UB, legitimate reuse DAG, aggregate resource admission, successor seal and fresh official review remain open. whole_bootstrap_closed=false; owner_consumption_authorized=false; continuation_ready=false; resource_admission=false; formal_execution_ready=false; formal_result=false; native_execution_authorized=false. New real native requires specific authorization after gates.
'''.encode('utf-8')
updates=[]
for item in trace['documents']:
    target=Path(item['path']);before=target.read_bytes()
    assert sha(target)==item['after_sha256']
    with target.open('ab') as out:out.write(summary)
    assert target.read_bytes()==before+summary
    updates.append(dict(path=target.as_posix(),before_sha256=item['after_sha256'],after_sha256=sha(target),original_bytes_preserved=True))
write(p/'append_trace_01.json',dict(documents=updates,development_checks_sha256=checks_sha))
draft=Path('results/tables/rq2_h1_bootstrap_integration_v1_non_authoritative/draft_state_14.json')
write(draft,dict(status='DRAFT_NONAUTHORITATIVE',scope='complete selector sequence development closure',
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
