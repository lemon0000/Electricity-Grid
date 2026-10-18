"""Bound the actual Parent-alias v3 tests to the already tested configured entry."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
base = json.loads((HERE / 'n0_path_owner_probe_plan_02.json').read_bytes())
sources = dict(base['source_sha256'])
code = dict(base['code_lease_sha256'])
for path in (REPO / 'experiments/h1_selector_phase_handoff_development_v3.py',
        REPO / 'tests/test_h1_selector_phase_handoff_negative_development_v1.py'):
    code[str(path)] = sha256(path.read_bytes()).hexdigest()
sources.update(code)
for path in (Path(__file__), HERE / 'run_negative_handoff_alias_bounded_v1.py',
        HERE / 'run_n0_path_entry_v1.py', HERE / 'n0_path_owner_probe_monitor_01/terminal.json',
        HERE / 'n0_path_owner_probe_01_non_authoritative/path_closed_receipt.json',
        HERE / 'negative_handoff_unit_01/terminal.json',
        REPO / 'tests/h1_group_selector_integration_helpers_v3.py',
        REPO / 'tests/test_h1_hour0_end_to_end_development_v3.py',
        REPO / 'docs/model_spec/rq2_h1_negative_actual_precheck_development_v1.md'):
    sources[str(path)] = sha256(path.read_bytes()).hexdigest()
assert all(sha256(Path(p).read_bytes()).hexdigest() == pin for p, pin in sources.items())
assert all(sha256(Path(p).read_bytes()).hexdigest() == pin for p, pin in base['old_chain_sha256'].items())
assert json.loads((HERE / 'n0_path_owner_probe_monitor_01/terminal.json').read_bytes())['exit_code'] == 0
basetemp = Path('D:/h1_negative_handoff_alias_01_non_authoritative')
value = dict(question='Does Handoff v3 reject all missing-Actual combinations without common replay, preserve both unresolved None branches, and complete/reopen the same three-Actual v3 paired transaction?',
    status='DRAFT_NONAUTHORITATIVE', attempts=1, synthetic_jobs=0, real_native_calls=0,
    target='tests/test_h1_selector_phase_handoff_negative_development_v1.py',
    source_sha256=sources, code_lease_sha256=code, old_chain_sha256=base['old_chain_sha256'],
    inner_output=str(HERE / 'negative_handoff_alias_01_non_authoritative'),
    outer_output=str(HERE / 'negative_handoff_alias_monitor_01'), basetemp=str(basetemp),
    path_roots=[str(REPO), str(basetemp)], minimum_lock_count=3,
    limits=dict(wall_seconds=240, sampled_rss_bytes=1024**3, storage_bytes=128 * 1024**2),
    source_and_execution_seams='explicit synthetic source and in-process fake Parent lifecycle/native solver; original selector archive and phase persistence/replay code',
    previous_attempt='ordinary unoptimized pytest capped240.140s before first Rref completion; preserved unchanged, not a test pass',
    changed_path='configured bounded-v2 code read sizes, locked metadata parser, existing canonical path lease; no profile/trace hook in integration tests',
    dag=['fixed source and unused roots', 'already verified configured entry',
        'reference plus three Actual Parent aliases using in-process fake lifecycle',
        'missing-all and three missing-one with unchanged common replay counter',
        'same Handoff v3 complete paired commit', 'all owners close', 'reopen saved tickets and identical carry',
        'two separate legitimate business unresolved None branches retain full path',
        'stop/join sampler and release path/code/metadata resources', 'all sources/old pins/PIDs/discovered locks postcheck'],
    stops='first error or fixed240s/1GiB sampled RSS/128MiB; no extension or unchanged retry',
    full_hour0_chain_passed=False, whole_workflow_performance_review_complete=False,
    formal_result=False, resource_admission=False, native_execution_authorized=False)
target = HERE / 'negative_handoff_alias_plan_01.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(value, stream, indent=2)
print(json.dumps(dict(plan_sha256=sha256(target.read_bytes()).hexdigest(), source_files=len(sources), code_files=len(code))))
