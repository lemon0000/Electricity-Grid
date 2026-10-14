"""Root-only append of this development unit's completed evidence."""
from pathlib import Path
import hashlib
import json

p = Path(__file__).parent
def sha(b): return hashlib.sha256(b).hexdigest()
def write(name, value):
    with (p/name).open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)

write('finalization_attempt_01.json', dict(exit_code=1, phase='stdin_script_parse',
    error='SyntaxError: unexpected character after line continuation character',
    script_executed=False, evidence_or_document_writes=False))
write('finalization_attempt_02.json', dict(exit_code=1, phase='file_script_parse',
    error='SyntaxError: invalid decimal literal', script_executed=False,
    evidence_or_document_writes=False, retained_script='finalize_records.py.parse_failed'))
final = json.loads((p/'before_test_02.json').read_text(encoding='utf-8'))
assert all(sha(Path(f).read_bytes()) == h for f,h in final.items())
write('preseal_review_02.json', dict(status='PRE_SEAL_SCOPED_FINDINGS_CLOSED',
    reviewer='/root/selector_owner_design_review', read_only=True, reading_stopped=True,
    findings_closed=['F1','F2'], new_findings=[], reviewed_hashes=final, files_unchanged=True,
    independent_test=dict(passed=23, deselected=27, seconds=29.47, exit_code=0,
        command='D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_h1_phase_manifest_binding_development_v1.py -k "scientific_inventory_fail_closed or group_semantic_claims_fail_closed or disposition_dependency_must_correspond or real_nonzero_capacity_mixed_proof_group_complete_mapping"'),
    native_calls=0, jobs=0, official_verdict=False,
    scope='Detached training UB declarations and conditional archive reservations only'))
old = Path('results/tables/rq2_h1_selector_configuration_v1_non_authoritative/development_checks.json')
pins = dict(json.loads(old.read_text(encoding='utf-8'))['files_sha256'])
pins.update(final)
assert len(pins) == 1001
assert all(Path(f).is_file() and sha(Path(f).read_bytes()) == h for f,h in pins.items())
evidence = {f.name:sha(f.read_bytes()) for f in sorted(p.iterdir()) if f.is_file()}
write('development_checks.json', dict(schema='h1_phase_manifest_binding_development_checks_v1',
    status='PRE_SEAL_SCOPED_FINDINGS_CLOSED',
    scope='detached training_ub direct shared lane declarations; all sibling obligations retained',
    previous_checks_sha256=sha(old.read_bytes()), pin_count=len(pins), files_sha256=pins,
    evidence_sha256=evidence, root_targeted=dict(passed=50, seconds=43.15, exit_code=0),
    related_regression=dict(passed=62, seconds=18.73, exit_code=0, dependency_bytes_unchanged=True),
    independent_targeted=dict(passed=23, deselected=27, seconds=29.47, exit_code=0),
    native_calls=0, jobs=0, executable_manifest=False, paired_owner_authenticated=False,
    selector_producer_connected=False, normal_source_correspondence_verified=False,
    alternate_witness_limit_enforced=False, full_event_size_bound_proven=False,
    full_path_archive_sufficiency_proven=False, resource_admission=False,
    formal_execution_ready=False, formal_result=False, native_execution_authorized=False,
    official_verdict=False))
checksha = sha((p/'development_checks.json').read_bytes())
addition = f"""

### 2026-10-11 - Training UB phase manifest candidate binding reviewed

Added experiments/h1_phase_manifest_binding_development_v1.py and matching tests/spec. Public prepare freshly reloads and independently reprojects the pinned group before and after construction. It maps unresolved N/C/J to exact shared Actual lane declarations, retaining every four-arm sibling and proof disposition. Unresolved training-UB B6 remains separate-planning pending, never an Actual lane. Nonzero D is only a capacity declaration; full selector/network/Job/non-solver, accounting period, labels, archive and implementation are bound into an audit identity, not a scientific decision key or owner credential. Empty direct rosters have no Manifest. Other families remain unimplemented.

PRE_SEAL F1/F2 are closed: exact scientific-field inventories and group claim/dependency boundaries now fail closed; real pinned ordinal11832353 exercises D=1/100, one network lane and three proof-terminal siblings, with a complete field mapping oracle. Initial root27 passed28.22s and independent5 passed/22 deselected25.69s are retained along with pre-fix byte snapshots/findings. Final root50 passed43.15s; related unchanged group/config dependencies62 passed18.73s; independent final23 passed/27 deselected29.47s. All exit0 with tested bytes unchanged. Zero research Job and zero real native; timings are diagnostics. No official verdict.

The full192 primary event upper bound is576; each reserved alternate witness adds2. This remains conditional on a future enforced witness count. Archive declarations must cover all declared events and the complete maximum-length base64 selector-record envelope, but source metadata/event framing, full event size, physical storage, host and runtime bounds remain unproved. Existing owner does not enforce the separate witness reservation. These checks do not establish full-path archive sufficiency or resource admission.

Evidence root: results/tables/rq2_h1_phase_manifest_binding_v1_non_authoritative/. development_checks SHA256 {checksha} binds1001 pins, including998 predecessors. Retention revalidates v2/v3 outer895/1695 and old run248/251 without drift. Root remains sole repository writer. All prior bytes, tests, failures and uncommitted artifacts are retained.

Next bind this candidate inside the original bootstrap owner operation with durable head/attempt/source/phase tickets, then attach common Rref production and fresh inspection, business-to-A release, paired commit and hour1+ continuation. B6 separate planning, other families, legal reuse/full same-contract LB-UB, complete192 producer coverage, enforced witness limits and aggregate resources remain open. Whole bootstrap and executable-manifest closure remain false. resource_admission=false; formal_execution_ready=false; formal_result=false; native_execution_authorized=false. Successor seal and a fresh official reviewer are still required; new real native requires separate concrete authorization after gates.
"""
previous = Path('results/tables/rq2_h1_selector_configuration_v1_non_authoritative/append_trace_01.json')
documents = []
for item in json.loads(previous.read_text(encoding='utf-8'))['documents']:
    f = Path(item['path']); before = f.read_bytes()
    assert sha(before) == item['after_sha256']
    with f.open('ab') as out: out.write(addition.encode('utf-8'))
    after = f.read_bytes()
    assert after == before + addition.encode('utf-8')
    documents.append(dict(path=f.as_posix(), before_sha256=sha(before),
        after_sha256=sha(after), original_bytes_preserved=True))
write('append_trace_01.json', dict(documents=documents, development_checks_sha256=checksha))
print(json.dumps(dict(development_checks_sha256=checksha, pin_count=len(pins), documents=documents)))
