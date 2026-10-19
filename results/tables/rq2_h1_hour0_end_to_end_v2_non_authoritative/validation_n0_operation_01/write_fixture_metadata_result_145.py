"""Preserve exact diagnostic bytes and decline an unhelpful draft extension."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = HERE / 'whole_workflow_optimization_01_non_authoritative'
plan_path = D / 'saved137_fixture_diagnostic_plan_145.json'
plan = json.loads(plan_path.read_bytes())
terminal_path = HERE / 'saved137_fixture_metadata_145/terminal.json'
terminal = json.loads(terminal_path.read_bytes())
drift = [p for p, pin in plan['files_sha256'].items()
         if sha256(Path(p).read_bytes()).hexdigest() != pin]
assert not drift and terminal['exit_code'] == 0 and terminal['source_unchanged']
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']

archive = D / 'fixture_metadata_143_145_preserved_non_authoritative'
archive.mkdir(exist_ok=False)
copies = []

def preserve(source, relative):
    raw = source.read_bytes()
    target = archive / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)
    assert target.read_bytes() == raw and source.read_bytes() == raw
    copies.append(dict(source=str(source), saved=str(target), size=len(raw),
                       sha256=sha256(raw).hexdigest()))
    return target

case_base = Path('D:/h1_fixture_metadata_143_non_authoritative')
cases = sorted(case_base.glob('*/tested_child_entry.py'))
assert len(cases) == 4
for entry in cases:
    case = entry.parent
    for name in ('tested_child_entry.py', 'child_stdout.txt', 'child_stderr.txt',
                 'child_entry_source_sha256.txt', 'test_probe.py',
                 'child_non_authoritative/unit_code_read_lease_closed.json'):
        preserve(case / name, Path('143') / case.name / name)

base = Path('D:/h1_saved137_fixture_145_non_authoritative')
profile_path = next(base.glob('*/saved137_candidate_oracle_profile.json'))
profile = json.loads(profile_path.read_bytes())
closed_path = base / 'unit_code_read_lease_closed.json'
closed = json.loads(closed_path.read_bytes())
assert not closed['diagnostic_validation_errors']
for source, relative in ((profile_path, '145/profile.json'),
                         (closed_path, '145/entry_closed.json'),
                         (HERE / 'run_unit_entry_v5.py', '145/tested_entry.py'),
                         (HERE / 'saved137_fixture_metadata_145/stdout.log', '145/stdout.log'),
                         (terminal_path, '145/terminal.json')):
    preserve(source, Path(relative))
old = json.loads((D / 'saved137_candidate_diagnostic_result_138.json').read_bytes())
rows = [dict(scope=r['scope'], fixture=r.get('fixture'),
             fast=r['receipt']['fast_path_calls'], fallback=r['receipt']['fallback_calls'])
        for r in closed['distribution_resolver_receipts']]
value = dict(schema='h1_fixture_metadata_diagnostic_result_145',
    at_utc=datetime.now(timezone.utc).isoformat(),
    status='RETIRED_NOT_ADOPTED_DRAFT',
    plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),
    terminal=terminal, planned_pins=len(plan['files_sha256']), pin_drift=drift,
    candidate_files=plan['candidate_files'], profile=profile, scopes=rows,
    archive_files=copies,
    comparison=dict(baseline_pytest_seconds=83.50, current_pytest_seconds=84.22,
        baseline_outer_seconds=old['terminal']['elapsed_seconds'],
        current_outer_seconds=terminal['elapsed_seconds'],
        baseline_profiled_oracle_seconds=old['profile']['oracle_seconds'],
        current_profiled_oracle_seconds=profile['oracle_seconds'],
        repeated_matched_benchmark=False, measured_speedup_supported=False),
    decision='Do not adopt fixture metadata scopes. The additional 272 fast calls did not produce an observed runtime benefit. Keep entry4 and its original resolver unchanged.',
    pre_seal_findings=dict(input144_sha256=sha256((D/'fixture_metadata_entry5_pre_seal_input_144.json').read_bytes()).hexdigest(),
        reviewer='public_phase_review_118', official_review=False,
        open_unadopted=['P2: fixture names do not bind exact target definitions.',
                       'P2: receipt reader failure can replace the fixture primary.'],
        portability_gap='Exact four child entry, receipt, stdout/stderr and probe bytes are now saved repo-local with source/saved SHA256 equality. Historical input144 is preserved.',
        fixes_not_implemented=True, dependent_use_permitted=False),
    new_N0_Jobs=0, real_native_calls=0,
    numerical_candidate_equal=True, independent_scientific_algorithm=False,
    registered_N0_owner_authenticated=False, public_bootstrap_return_verified=False,
    whole_workflow_performance_review_complete=False, full_optimized_workflow_accepted=False,
    production_seal=False, formal_result=False, formal_execution_ready=False,
    resource_admission=False, native_execution_authorized=False)
target = D / 'fixture_metadata_diagnostic_result_145.json'
with target.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(value, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(path=str(target), sha256=sha256(target.read_bytes()).hexdigest(),
                      pins=len(plan['files_sha256']), drift=drift, preserved=len(copies), scopes=rows)))
