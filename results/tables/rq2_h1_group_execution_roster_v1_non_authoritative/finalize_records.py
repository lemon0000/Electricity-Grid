"""Root-only development evidence finalization after terminal verification."""
from pathlib import Path
import hashlib
import json
import re

p = Path(__file__).parent
def sha(f): return hashlib.sha256(Path(f).read_bytes()).hexdigest()
def read(name): return json.loads((p/name).read_text(encoding='utf-8'))
def write(name, value):
    with (p/name).open('x', encoding='utf-8') as out:
        json.dump(value, out, indent=2, ensure_ascii=False)

final = read('before_test_02.json')
assert all(sha(f)==h for f,h in final.items())
review = read('preseal_static_review_02.json')
independent = read('independent_test_02.json')
assert review['findings_closed']==['F1','F2','F3','F4'] and not review['new_must_fix_findings']
assert review['reviewed_hashes']==final and independent['reviewed_hashes']==final
assert independent['reading_stopped']
assert independent['independent_test']['exit_code']==0
assert independent['independent_test']['files_unchanged']
tests = {}
for stem in ('root_test_02','root_regression_01'):
    report = read(stem+'.json')
    assert report['exit_code']==0 and report['files_unchanged']
    log = (p/(stem+'.log')).read_text(encoding='utf-8')
    match = re.search(r'(\d+) passed(?:, (\d+) deselected)? in ([0-9.]+)s',log)
    assert match
    tests[stem] = dict(report,passed=int(match[1]),deselected=int(match[2] or 0),pytest_seconds=float(match[3]))
assert tests['root_test_02']['passed']==23 and tests['root_regression_01']['passed']==50
old = Path('results/tables/rq2_h1_bootstrap_phase_manifest_binding_v1_non_authoritative/development_checks.json')
assert sha(old)=='bc75d1150887d91469099450bdf85846fb835e901a9b1df0c48f5c5cd33c690c'
previous = json.loads(old.read_text(encoding='utf-8'))
pins = dict(previous['files_sha256'])
assert len(pins)==1002 and all(sha(f)==h for f,h in pins.items())
for f,record in previous['reviewed_open_assembly'].items():
    assert sha(f)==record['sha256']==sha(record['snapshot'])
pins.update(final)
assert len(pins)==1005
retention = read('frozen_retention_02.json')
assert not retention['drift']
assert all(not item['member_drift'] and not item['run_drift'] for item in retention['frozen'].values())
evidence = {f.name:sha(f) for f in sorted(p.iterdir()) if f.is_file()}
write('development_checks.json',dict(schema='h1_group_execution_roster_checks_v1',
    status='PRE_SEAL_SCOPED_FINDINGS_CLOSED',
    scope='bootstrap-addressable independent N0 journal correspondence only',
    previous_checks_path=old.as_posix(),previous_checks_sha256=sha(old),
    pin_count=len(pins),files_sha256=pins,evidence_sha256=evidence,
    root_tests=tests,independent_test=independent['independent_test'],
    zero_direct_catalog_membership_proven=False,
    group_execution_ready=False,selector_producer_authorized=False,
    N_reuse_verified=False,Rref_reuse_verified=False,resource_discounts_applied=False,
    common_reference_input_verified=False,paired_owner_authenticated=False,
    full_family_group_registry_complete=False,all_catalog_groups_enumerated=False,
    whole_bootstrap_closed=False,resource_admission=False,formal_execution_ready=False,
    formal_result=False,native_execution_authorized=False,official_verdict=False,
    native_calls=0,research_jobs=0))
trace_path = old.parent/'append_trace_01.json'
trace = json.loads(trace_path.read_text(encoding='utf-8'))
checks_sha = sha(p/'development_checks.json')
summary = f'''

### 2026-10-11 - Independent N0 group roster development reviewed

The new standalone group roster maps each direct sibling to its own retained claim, release, local N0 terminal and global N0 terminal through fresh bootstrap replay. The study-local singleton journal binds the full four-sibling phase audit and canonical ordinal. Missing global terminal stays pending; duplicate attachments, cross-arm aliases including release, conflicting heads/declarations and changed operation nonce are rejected. Attachment/write/retention failures preserve written bytes and poison the handle. All predecessor bootstrap bytes are retained.

PRE_SEAL F1-F4 closed after root full protocol tests {tests['root_test_02']['passed']} passed in {tests['root_test_02']['pytest_seconds']}s, related phase-manifest regression {tests['root_regression_01']['passed']} passed in {tests['root_regression_01']['pytest_seconds']}s, and independent nonce/header-only tests 3 passed/20 deselected in 233.31s. All exit0 and fixed hashes unchanged. Tests use explicit synthetic N0 evidence; they establish journal correspondence, not numerical acceptance, common scientific input or actual source/Job execution. The header-only B6 test uses a synthetic classification boundary and does not prove a matching frozen catalog coordinate. Fully proof-terminal groups remain represented by the closed binder; no obligation is removed.

Evidence: {p.as_posix()}/development_checks.json, SHA256 {checks_sha}, 1005 pins. Old v2/v3 outer895/1695 and run248/251 remain unchanged. Original draft snapshots and all test/review evidence are retained. Zero native and zero research Job. This is scoped development closure, not an official verdict.

Next bind actual per-arm scientific N input/projection correspondence before a common Rref/A owner consumes the group. Independent runs retain full resource costs; true reuse requires a separate verified consumer-terminal/DAG path. Live source/phase tickets, owned selector production, paired commit, hour1+ continuation, B6 planning, other families, same-contract LB/UB, complete192 producer/resource coverage, successor seal and fresh official review remain open. group_execution_ready=false; common_reference_input_verified=false; paired_owner_authenticated=false; resource_admission=false; formal_execution_ready=false; formal_result=false; native_execution_authorized=false. New real native requires specific authorization after gates.
'''.encode('utf-8')
updates=[]
for item in trace['documents']:
    target=Path(item['path']);before=target.read_bytes()
    assert sha(target)==item['after_sha256']
    with target.open('ab') as out:out.write(summary)
    assert target.read_bytes()==before+summary
    updates.append(dict(path=target.as_posix(),before_sha256=item['after_sha256'],
                        after_sha256=sha(target),original_bytes_preserved=True))
write('append_trace_01.json',dict(documents=updates,development_checks_sha256=checks_sha))
print(json.dumps(dict(development_checks_sha256=checks_sha,pin_count=len(pins),documents=updates)))
