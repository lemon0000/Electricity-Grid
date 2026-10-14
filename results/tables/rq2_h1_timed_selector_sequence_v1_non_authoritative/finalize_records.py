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
for stem,count in [('root_test_03',48),('root_regression_01',77)]:
    report=read(p/(stem+'.json'))
    assert report['exit_code']==0 and report['files_unchanged']
    match=re.search(r'(\d+) passed in ([0-9.]+)s',(p/(stem+'.log')).read_text(encoding='utf-8'))
    assert match and (count is None or int(match[1])==count)
    tests[stem]=dict(report,passed=int(match[1]),pytest_seconds=float(match[2]))

old=Path('results/tables/rq2_h1_selector_timing_v1_non_authoritative/development_checks.json')
assert sha(old)=='f10437600e2a4129a147567cb922f8f181e987d1b29713ef08e4cc8b07be29e8'
pins=dict(read(old)['files_sha256']);assert len(pins)==1021
assert all(sha(f)==h for f,h in pins.items())
pins.update(pins_now);assert len(pins)==1024
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
write(p/'development_checks.json',dict(schema='h1_timed_selector_sequence_checks_v1',
    status='PRE_SEAL_SCOPED_FINDINGS_CLOSED',scope='complete explicit timed selector sequence with paired scientific and timing journals',
    previous_checks_path=old.as_posix(),previous_checks_sha256=sha(old),pin_count=len(pins),files_sha256=pins,
    evidence_sha256=evidence,root_tests=tests,independent_test=review['independent_test'],
    regression_scope='unchanged owned scientific selector sequence and timed stage; separate process; predecessor 1021 pins rechecked',
    fabricated_direct_adapter=True,dual_journal_failure_windows_tested=True,
    actual_RTS_group_integration_verified=False,full_192_hour_execution_verified=False,
    native_calls=0,research_jobs=0,**gates))
checks_sha=sha(p/'development_checks.json')
ind=review['independent_test']
summary=f'''

### 2026-10-11 - Complete timed selector sequence development reviewed

The new standalone live owner executes every configured selector stage using the explicit timed producer, independently replays the joint stage result, and writes paired scientific and timing commits. Scientific records retain the closed legacy wire contract and pass its independent inspector. Timing commits bind exact science commit bytes, request/index/label, both stage terminals, previous timing head, owner and QPC windows. This owner never constructs the old owner or its completion type.

The two journals are not atomic: every before/after commit or terminal write failure permanently poisons the owner and retains evidence. Missing counterparts, suffixes and unequal prefixes cannot resume. Both roots and original callbacks, guard, PID/thread, nonce, exact configuration and retained file/directory stamps are checked before subsequent stage release. Final timing terminal binds both final heads, complete timing vector, science terminal, integer native aggregate and diagnostic window. Detached replay does not reconstruct a live owner or certify historical execution.

Root full suite: {tests['root_test_03']['passed']} passed in {tests['root_test_03']['pytest_seconds']}s; closed predecessor regression: {tests['root_regression_01']['passed']} passed in {tests['root_regression_01']['pytest_seconds']}s; independent targeted: {ind['passed']} passed/{ind['deselected']} deselected in {ind['pytest_seconds']}s. All exit0 and reviewed bytes unchanged. Coverage includes both roles, full UID inventory including a disabled second generator, exact analytic lock vectors, old inspector compatibility, independent timing payload cap before mkdir, dual-journal publication windows, second-stage failures, callback/nonce/guard/configuration mutation, same-byte header replacement, valid standalone stage with overlapping sequence window, detached tampering and new live receipt identity. Initial drafts and all logs remain retained. PRE_SEAL F1 now checks the maximum-width timing header before mkdir and validates the exact directory identity representation. F2 binds initial/final snapshot projections, including paths, caps, content hashes and complete file/directory stamps, to fixed owner state and the private completion fingerprint. Both original gaps were reproduced before fixing; the 2-passed counterexample run establishes defective behavior rather than acceptance. Its initial import-path collection error is retained. The earlier 41-passed root suite did not close those findings; new regression tests reject synchronized snapshot/file replacement.

Evidence: {p.as_posix()}/development_checks.json, SHA256 {checks_sha}, 1024 pins. All predecessor pins, reviewed open-bootstrap snapshots, v2/v3 outer895/1695 and run248/251 remain unchanged. Tests use fabricated direct adapters, zero real native and zero research Job. This is scoped PRE_SEAL development closure only, not official review or execution authority.

The constructor-to-preterminal window includes possible idle time and excludes final publication/readback. Logical archive caps exclude filesystem allocation and RAM. Neither establishes whole-Job timing or non-solver allowance. Next design handoff: results/tables/rq2_h1_selector_worker_transport_v1_non_authoritative/design_review_01.md. Integrate source-rebuilt owned worker transport and selector Windows Job control with complete release/clock/budget/quiescence evidence, fresh parent replay, and paired phase transaction consumption. Hour1+ and complete192 execution, verified reuse DAG, same-contract LB/UB, full aggregate admission, successor seal and fresh official review remain open. owner_consumption_authorized=false; selector_producer_connected=false; continuation_ready=false; whole_job_quiescence_checked=false; resource_admission=false; formal_execution_ready=false; formal_result=false; native_execution_authorized=false. New native requires concrete gates and specific authority.
'''.encode('utf-8')
updates=[]
for item in trace['documents']:
    target=Path(item['path']);before=target.read_bytes()
    assert sha(target)==item['after_sha256']
    with target.open('ab') as out:out.write(summary)
    assert target.read_bytes()==before+summary
    updates.append(dict(path=target.as_posix(),before_sha256=item['after_sha256'],after_sha256=sha(target),original_bytes_preserved=True))
write(p/'append_trace_01.json',dict(documents=updates,development_checks_sha256=checks_sha))
draft=Path('results/tables/rq2_h1_bootstrap_integration_v1_non_authoritative/draft_state_17.json')
write(draft,dict(status='DRAFT_NONAUTHORITATIVE',scope='complete timed selector sequence development closure',
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
