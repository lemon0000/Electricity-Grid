"""Root-only create-once scoped development evidence; no formal authority."""
from pathlib import Path
import hashlib
import ast
import json
import re
import subprocess

p=Path(__file__).parent
def sha(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
def read(f):return json.loads(Path(f).read_text(encoding='utf-8'))
def write(f,value):
    with Path(f).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,ensure_ascii=False)

current=read(p/'before_test_02.json')
assert all(sha(f)==h for f,h in current.items())
review=read(p/'independent_review_02.json')
assert review['status']=='PRE_SEAL_SCOPED_FINDINGS_CLOSED' and review['reading_stopped']
assert review['reviewed_hashes']==current
assert review['independent_test']['exit_code']==0 and review['independent_test']['files_unchanged']
tests={}
for stem,count in [('root_test_01',11),('root_test_02',3),('root_regression_01',49)]:
    result=read(p/(stem+'.json'))
    assert result['exit_code']==0 and result['files_unchanged']
    match=re.search(r'(\d+) passed(?:, \d+ deselected)? in ([0-9.]+)s',(p/(stem+'.log')).read_text(encoding='utf-8'))
    assert match and int(match[1])==count
    tests[stem]=dict(result,passed=count,pytest_seconds=float(match[2]))

previous=read(p/'before_test_01.json')
test_path='tests/test_h1_selector_worker_output_inspection_development_v1.py'
old_test=p/'test_h1_selector_worker_output_inspection_development_v1.py.before_E1_E2'
assert sha(old_test)==previous[test_path]
assert all(h==previous[f] for f,h in current.items() if f!=test_path)
old_tree=ast.parse(old_test.read_text(encoding='utf-8'))
new_tree=ast.parse(Path(test_path).read_text(encoding='utf-8'))
added={'test_complete_transport_and_timing_crosspin_field_matrix','test_late_same_byte_archive_replacement_during_second_rebuild'}
new_tree.body=[n for n in new_tree.body if not (isinstance(n,ast.FunctionDef) and n.name in added)]
assert ast.dump(old_tree,include_attributes=False)==ast.dump(new_tree,include_attributes=False)

old=Path('results/tables/rq2_h1_selector_job_lifecycle_v1_non_authoritative/development_checks.json')
assert sha(old)=='498209842f922e87481aac014d3ab5cd6d50750245c3759ed5cdbaa6fabdd9fa'
pins=dict(read(old)['files_sha256']);assert len(pins)==1030
assert all(sha(f)==h for f,h in pins.items())
pins.update(current);assert len(pins)==1033
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
    owner_consumption_authorized=False,selector_parent_connected=False,non_solver_allowance_verified=False)
write(p/'development_checks.json',dict(schema='h1_selector_output_inspection_checks_v1',
    status='PRE_SEAL_SCOPED_FINDINGS_CLOSED',scope='full fresh conditional selector worker output replay; no live Job credential',
    previous_checks_path=old.as_posix(),previous_checks_sha256=sha(old),pin_count=len(pins),files_sha256=pins,
    evidence_sha256=evidence,root_tests=tests,root_case_coverage=dict(total_cases=14,unchanged_cases=11,added_cases=3,additional_field_mutations=30,prior_test_ast_unchanged=True,production_code_and_spec_unchanged=True),independent_test=review['independent_test'],findings_closed=review['findings_closed'],
    root_synthetic_sources_and_fabricated_adapters=True,related_regression_real_windows_jobs=True,real_native_calls=0,formal_runs=0,
    actual_RTS_group_integration_verified=False,full_192_hour_execution_verified=False,**gates))
checks_sha=sha(p/'development_checks.json');ind=review['independent_test']
summary=f'''

### 2026-10-12 - Fresh conditional selector worker output inspection development reviewed

The new reader accepts six parent-produced input pins and explicit environment/process/PID/creation declarations. Fresh mode performs the first bounded reads of consumed/result/timing outputs and derives their three pins internally. Retained mode additionally requires those three output pins. It returns the complete nine-pin set in a bounded detached lifecycle diagnostic envelope. Fresh derived hashes are bookends, not external authentication; the reader never accepts or issues a live Job observation or execution receipt.

It independently reconstructs the complete request projection from fresh typed source/configuration, recomputes launch identity and strict initial headroom, validates child/release/consume/result cross-pins, and replays the full scientific/timing sequence. Record hashes, native aggregate, terminals and the full archive-view fingerprint must match. Eight exact integer phases must be ordered/contiguous, have the exact entry delta and contain every stage/native interval with matching PID/thread. Source is reconstructed again and metadata/root/archive stamps are bookended before return. Import-fixed validators/readers/codecs and worker caps/phase/namespaces/scope remain checked. The entire reader forbids solver calls.

Root initial complete suite: {tests['root_test_01']['passed']} passed in {tests['root_test_01']['pytest_seconds']}s; appended evidence tests: {tests['root_test_02']['passed']} passed in {tests['root_test_02']['pytest_seconds']}s. All14 cases are covered; AST comparison proves the original11 unchanged and production code/spec are identical; related unchanged lifecycle regression: {tests['root_regression_01']['passed']} passed in {tests['root_regression_01']['pytest_seconds']}s; independent targeted: {ind['passed']} passed/{ind['deselected']} deselected in {ind['pytest_seconds']}s. All exit0 and reviewed bytes unchanged. The root tests use both roles with synthetic sources, real journal/replay paths and fabricated adapters; they include fresh/retained replay, external pin/process mismatch, rehashed result/phase and parent transport tampering, same-byte archive replacement, source drift, preinstalled reader replacement and mid-rebuild file/namespace/validator drift. Mutation loops cover multiple faults within individual tests. Related lifecycle regression uses stdlib-only short Windows Jobs. Zero real native and zero formal runs. PRE_SEAL E1 was closed by30 explicit field mutations with recomputed parent/output pins; E2 by same-byte science/timing binding replacement during the third fresh-source call, after initial archive capture and replay. All drafts/review/test records remain preserved.

Evidence: {p.as_posix()}/development_checks.json, SHA256 {checks_sha},1033 pins. All predecessor pins, reviewed open-bootstrap snapshots, v2/v3 outer895/1695 and run248/251 remain unchanged. This is scoped PRE_SEAL development closure, not official review or execution authority.

Next wire the selector-specific parent controller: fixed worker argv, durable launch/release records, invoke this fresh reader only within the owned lifecycle on_quiescent callback, jointly bind live Job observation plus diagnostic in a parent terminal, and retain exact live Rref completion provenance before Actual release. Actual source replay alone proves only scientific/business mapping. Persistent paired phase consumption, hour1+,192-hour coverage, legal reuse DAG, same-contract LB/UB, complete resource admission, successor seal and fresh official review remain open. selector_parent_connected=false; owner_consumption_authorized=false; non_solver_allowance_verified=false; resource_admission=false; formal_execution_ready=false; formal_result=false; native_execution_authorized=false. New real native still requires a concrete admitted package and specific authority.
'''.encode('utf-8')
updates=[]
for item in trace['documents']:
    target=Path(item['path']);before=target.read_bytes()
    assert sha(target)==item['after_sha256']
    with target.open('ab') as stream:stream.write(summary)
    assert target.read_bytes()==before+summary
    updates.append(dict(path=target.as_posix(),before_sha256=item['after_sha256'],after_sha256=sha(target),original_bytes_preserved=True))
write(p/'append_trace_01.json',dict(documents=updates,development_checks_sha256=checks_sha))
draft=Path('results/tables/rq2_h1_bootstrap_integration_v1_non_authoritative/draft_state_20.json')
write(draft,dict(status='DRAFT_NONAUTHORITATIVE',scope='fresh conditional selector worker output inspection',
    development_checks_path=(p/'development_checks.json').as_posix(),development_checks_sha256=checks_sha,**gates))
diff=subprocess.run(['git','diff','--check'],capture_output=True,text=True);assert diff.returncode==0,diff.stdout+diff.stderr
status=subprocess.check_output(['git','status','--short'],text=True)
assert all(sha(f)==h for f,h in pins.items())
write(p/'final_verification_01.json',dict(development_checks_sha256=checks_sha,pin_count=len(pins),pin_drift=[],
    evidence_count=len(evidence),evidence_drift=[f for f,h in evidence.items() if sha(p/f)!=h],frozen=frozen,
    open_assembly_drift=[],document_hashes_match=True,draft_state_path=draft.as_posix(),draft_state_sha256=sha(draft),
    git_diff_check_exit=diff.returncode,git_status_count=len(status.splitlines())))
print(json.dumps(dict(development_checks_sha256=checks_sha,pin_count=len(pins),draft_state_sha256=sha(draft))))
