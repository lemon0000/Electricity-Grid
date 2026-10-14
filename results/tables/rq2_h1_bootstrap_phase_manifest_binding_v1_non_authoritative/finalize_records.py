"""Root-only finalization after terminal tests and independent scoped review."""
from pathlib import Path
import hashlib
import json
import re

p = Path(__file__).parent
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(name): return json.loads((p/name).read_text(encoding='utf-8'))
def write(name, value):
    with (p/name).open('x', encoding='utf-8') as out:
        json.dump(value, out, indent=2, ensure_ascii=False)

final = read('before_test_03.json')
assert all(sha(f) == h for f,h in final.items())
review = read('preseal_review_03.json')
assert review['status'] == 'PRE_SEAL_SCOPED_FINDINGS_CLOSED'
assert review['reviewed_hashes'] == final and review['reading_stopped']
assert review['independent_test']['exit_code'] == 0
assert all(x['exit_code'] == 0 for x in review['additional_independent_tests'])
tests = {}
for stem in ('root_test_03', 'root_test_04', 'root_regression_02'):
    report = read(stem+'.json')
    assert report['exit_code'] == 0 and report['files_unchanged']
    log = (p/(stem+'.log')).read_text(encoding='utf-8')
    summary = re.search(r'(\d+) passed(?:, (\d+) deselected)? in ([0-9.]+)s', log)
    assert summary is not None
    tests[stem] = dict(report, passed=int(summary[1]), deselected=int(summary[2] or 0),
                      pytest_seconds=float(summary[3]))
assert tests['root_test_04']['passed'] == 36
retention = read('frozen_retention_01.json')
assert not retention['predecessor_drift']
assert all(x['outer_pin_matches'] and not x['member_drift'] and not x['run_drift']
           for x in retention['frozen'].values())
old = Path('results/tables/rq2_h1_phase_manifest_binding_v1_non_authoritative/development_checks.json')
pins = dict(json.loads(old.read_text(encoding='utf-8'))['files_sha256'])
test_path = 'tests/test_h1_bootstrap_phase_manifest_binding_development_v1.py'
pins[test_path] = final[test_path]
assert len(pins) == 1002
assert all(Path(f).is_file() and sha(f) == h for f,h in pins.items())
snapshots = {}
for f,h in final.items():
    if f == test_path: continue
    target = p/(Path(f).name+'.reviewed_snapshot')
    with target.open('xb') as out: out.write(Path(f).read_bytes())
    assert sha(target) == h
    snapshots[f] = dict(sha256=h, snapshot=target.as_posix())
evidence = {f.name:sha(f) for f in sorted(p.iterdir()) if f.is_file()}
write('development_checks.json', dict(schema='h1_bootstrap_phase_manifest_binding_checks_v1',
    status='PRE_SEAL_SCOPED_FINDINGS_CLOSED',
    scope='internal phase audit binding to bootstrap header, proposal and foreign claim replay',
    previous_checks_path=old.as_posix(), previous_checks_sha256=sha(old),
    pin_count=len(pins), files_sha256=pins, reviewed_open_assembly=snapshots,
    evidence_sha256=evidence, root_tests=tests, independent_test=review['independent_test'],
    additional_independent_tests=review['additional_independent_tests'],
    native_calls=0, research_jobs=0, whole_bootstrap_closed=False,
    phase_manifest_owner_attached=False, group_execution_roster_authenticated=False,
    all_sibling_execution_verified=False, normal_reuse_verified=False,
    selector_producer_connected=False, paired_source_correspondence_verified=False,
    resource_admission=False, formal_execution_ready=False, formal_result=False,
    native_execution_authorized=False, official_verdict=False))
checksha = sha(p/'development_checks.json')
draft = Path('results/tables/rq2_h1_bootstrap_integration_v1_non_authoritative/draft_state_10.json')
with draft.open('x', encoding='utf-8') as out:
    json.dump(dict(status='DRAFT_NONAUTHORITATIVE',scope='phase manifest audit binding addition',
        files=snapshots,scoped_checks_path=(p/'development_checks.json').as_posix(),
        scoped_checks_sha256=checksha,whole_bootstrap_closed=False,
        phase_manifest_owner_attached=False,group_execution_roster_authenticated=False,
        selector_producer_connected=False,formal_result=False,formal_execution_ready=False,
        resource_admission=False,native_execution_authorized=False),out,indent=2)
r=tests['root_test_04']; b=tests['root_regression_02']; i=review['independent_test']
addition = f"""

### 2026-10-11 - Bootstrap phase manifest audit binding reviewed

The open bootstrap assembly now internally prepares the exact phase candidate and binds its full audit to the episode header and audit identity to the attempt/global claim. The common study declaration binds selector/archive configuration while ordinal-specific audits remain in separate episode headers. Foreign claim replay independently reconstructs the full header, proposal and attempt. Same-group different-arm ordinals retain distinct slots and claims; no reuse credit is granted. No caller-supplied candidate or audit is accepted as a credential.

PRE_SEAL F1-F4 are closed: selector/archive substitution is rejected; request/declaration and dependency reads are bookended before writes; cache/snapshot rewrites are checked against durable header bytes; callback changes and returned-candidate substitution are rejected before attempt. Full header, attempt and conservative claim byte capacities are checked before directory creation. The cache retains immutable audit bytes only; live fingerprint checks remain required. Protocol tests cache initial real fingerprints, while separate tests exercise the real reader and dependency drift. These tests do not establish runtime performance or resource admission.

Final root targeted: {r['passed']} passed in {r['pytest_seconds']}s; related bootstrap/selector/N0 regressions: {b['passed']} passed in {b['pytest_seconds']}s; independent: {i['passed']} passed, {i['deselected']} deselected in {i['seconds']}s, plus the header/claim/foreign/reopen positive test1 passed194.18s. All exit0 with reviewed bytes unchanged. Root F4 narrow3 passed/33 deselected93.74s is retained. Superseded root_test_01, root_regression_01 and root_test_02 were deliberately interrupted after concrete findings; exit4294967295 and partial logs remain, never counted as passes. All prior snapshots, failures and uncommitted work remain. Zero real native and zero research Job; no official verdict.

Evidence: results/tables/rq2_h1_bootstrap_phase_manifest_binding_v1_non_authoritative/. development_checks SHA256 {checksha} binds1002 pins, including1001 predecessors and the new binding test. Open bootstrap code/spec are retained as reviewed snapshots, not newly frozen live assembly. draft_state_10 retains whole_bootstrap_closed=false. Retention revalidates v2/v3 outer895/1695 and old run248/251 without drift.

Next resolve group execution ownership: one selected-arm N claim cannot authorize the other direct lanes in the group candidate. Exact per-arm claims and accepted source correspondence or a verified reuse DAG are required before a common Rref/A owner may consume them. Then attach live source/phase tickets, owned selector production and fresh inspection, paired commit and hour1+ continuation. B6 separate planning, other families, same-contract LB/UB, full192 producer coverage, witness/event/storage bounds, aggregate resources, successor seal and fresh official review remain open. resource_admission=false; formal_execution_ready=false; formal_result=false; native_execution_authorized=false. New real native requires separate concrete authorization after gates.
"""
previous = Path('results/tables/rq2_h1_phase_manifest_binding_v1_non_authoritative/append_trace_01.json')
documents=[]
for item in json.loads(previous.read_text(encoding='utf-8'))['documents']:
    f=Path(item['path']); before=f.read_bytes()
    assert hashlib.sha256(before).hexdigest()==item['after_sha256']
    with f.open('ab') as out:out.write(addition.encode('utf-8'))
    assert f.read_bytes()==before+addition.encode('utf-8')
    documents.append(dict(path=f.as_posix(),before_sha256=item['after_sha256'],
        after_sha256=sha(f),original_bytes_preserved=True))
write('append_trace_01.json',dict(documents=documents,development_checks_sha256=checksha,
    draft_state_path=draft.as_posix(),draft_state_sha256=sha(draft)))
print(json.dumps(dict(pin_count=len(pins),development_checks_sha256=checksha,documents=documents)))
