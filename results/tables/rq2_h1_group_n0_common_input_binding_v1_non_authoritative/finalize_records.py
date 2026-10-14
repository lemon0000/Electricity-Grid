"""Root-only scoped development evidence; never a formal readiness receipt."""
from pathlib import Path
import hashlib
import json
import re

p=Path(__file__).parent
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(name):return json.loads((p/name).read_text(encoding='utf-8'))
def write(name,value):
    with (p/name).open('x',encoding='utf-8') as out:json.dump(value,out,indent=2,ensure_ascii=False)

pins_now=read('before_test_03.json')
assert all(sha(f)==h for f,h in pins_now.items())
review=read('independent_test_03.json')
assert review['reading_stopped'] and review['status']=='PRE_SEAL_SCOPED_FINDINGS_CLOSED'
assert review['reviewed_hashes']==pins_now and review['independent_test']['exit_code']==0
assert review['independent_test']['files_unchanged']
tests={}
for stem in ('root_test_03','root_regression_01'):
    report=read(stem+'.json');assert report['exit_code']==0 and report['files_unchanged']
    match=re.search(r'(\d+) passed(?:, (\d+) deselected)? in ([0-9.]+)s',(p/(stem+'.log')).read_text(encoding='utf-8'))
    assert match
    tests[stem]=dict(report,passed=int(match[1]),deselected=int(match[2] or 0),pytest_seconds=float(match[3]))
assert tests['root_test_03']['passed']==39 and tests['root_regression_01']['passed']==80
old=Path('results/tables/rq2_h1_group_execution_roster_v1_non_authoritative/development_checks.json')
assert sha(old)=='372142d4a59295832a2da1646859a79ce9deb25f8204f1dfe147978159331c11'
previous=json.loads(old.read_text(encoding='utf-8'))
pins=dict(previous['files_sha256']);assert len(pins)==1005
assert all(sha(f)==h for f,h in pins.items())
pins.update(pins_now);assert len(pins)==1008
evidence={f.name:sha(f) for f in sorted(p.iterdir()) if f.is_file()}
write('development_checks.json',dict(schema='h1_group_n0_common_input_binding_checks_v1',
    status='PRE_SEAL_SCOPED_FINDINGS_CLOSED',scope='live-guarded per-arm historical/exact-current scientific correspondence diagnostics',
    previous_checks_path=old.as_posix(),previous_checks_sha256=sha(old),
    pin_count=len(pins),files_sha256=pins,evidence_sha256=evidence,
    root_tests=tests,independent_test=review['independent_test'],
    tests_use_synthetic_accepted_prefix=True,actual_RTS_integration_verified=False,
    persistent_common_owner_bound=False,group_execution_ready=False,
    common_reference_input_verified=False,selector_producer_authorized=False,
    paired_owner_authenticated=False,N_reuse_verified=False,Rref_reuse_verified=False,
    resource_discounts_applied=False,full_192_hour_execution_verified=False,
    whole_bootstrap_closed=False,resource_admission=False,formal_execution_ready=False,
    formal_result=False,native_execution_authorized=False,official_verdict=False,
    native_calls=0,research_jobs=0))
checksha=sha(p/'development_checks.json')
ind=review['independent_test']
summary=f'''

### 2026-10-11 - Independent N0 common-input correspondence development reviewed

The new standalone binding internally prepares the typed group Manifest under the original live roster/bootstrap guards, requires all direct independent N0 attachments, and reconstructs each full historical N0 plus exact current/outage/workload/CFE join from retained pins. Each historical audit is checked against its own retained raw SHA; shortened exact-current normal audits are bridged by shared fields. Cross-arm equality uses canonical N carry/decision/request/locks, current outage decision, exact exogenous payload, registry decision projection and the initial phase state/request. Per-arm source/action/archive audit identities remain separate provenance. Two complete rounds, fresh manifest and roster/global replay bookends reject drift. Returned diagnostics grant no detached-consumption or owner capability.

Root full suite: 39 passed in {tests['root_test_03']['pytest_seconds']}s; related exact-current/phase-manifest regression: 80 passed in {tests['root_regression_01']['pytest_seconds']}s; independent targeted: {ind['passed']} passed/{ind['deselected']} deselected in {ind['pytest_seconds']}s. All final tests exit0 with checked bytes unchanged. The real adapter composition test executes historical.prepare, exact-current.prepare, phase._initial and phase._request over an explicit synthetic accepted-prefix/source fixture. Guard rejection uses a real roster; multi-arm positive/fault cases use explicit orchestration seams. These tests do not prove actual accepted RTS group integration or runtime resource performance.

Initial failures remain: journal encoder newline versus source audit canonical encoding was fixed using each provider's encoder; synthetic trace_identity_basis and power/workload chain_id omissions were fixed in the test window wrapper with recomputed window identities. The independent failed run and root failed full run are retained and never counted as passes. Existing closed modules remain unchanged; zero native and zero research Job.

Evidence: {p.as_posix()}/development_checks.json, SHA256 {checksha}, 1008 pins. This is scoped PRE_SEAL development closure only. Next persist the complete group correspondence in a common-owner wrapper before creating/reopening canonical holder/owner genesis. A canonical SourceBinding alone cannot prove all siblings' correspondence. Producer ownership, paired commit, hour1+ continuation, B6/other-family obligations, same-contract LB/UB, verified reuse DAG, full192/resource admission, successor seal and fresh official review remain open. persistent_common_owner_bound=false; group_execution_ready=false; common_reference_input_verified=false; resource_admission=false; formal_execution_ready=false; formal_result=false; native_execution_authorized=false. New real native requires specific authorization after gates.
'''.encode('utf-8')
trace=json.loads((old.parent/'append_trace_01.json').read_text(encoding='utf-8'))
updates=[]
for item in trace['documents']:
    target=Path(item['path']);before=target.read_bytes();assert sha(target)==item['after_sha256']
    with target.open('ab') as out:out.write(summary)
    assert target.read_bytes()==before+summary
    updates.append(dict(path=target.as_posix(),before_sha256=item['after_sha256'],after_sha256=sha(target),original_bytes_preserved=True))
write('append_trace_01.json',dict(documents=updates,development_checks_sha256=checksha))
print(json.dumps(dict(development_checks_sha256=checksha,pin_count=len(pins))))
