"""Reconcile static expansion, bounded prefix evidence and the lock-read erratum.

No experiment, credential, numerical replay, cache or gate transition occurs.
"""
import ast
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
OUT = HERE / 'parent_bottleneck_postcheck_01_non_authoritative'
OUT.mkdir(exist_ok=False)


def read(name):
    return json.loads((HERE / name).read_bytes())


def call_count(path, owner, name, receiver):
    tree = ast.parse((REPO / path).read_bytes())
    container = tree if owner is None else next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == owner)
    fn = next(n for n in container.body if isinstance(n, ast.FunctionDef) and n.name == name)
    rows = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Call) and ast.unparse(n.func) == receiver]
    assert rows, (path, owner, name, receiver)
    return dict(file=path, owner=owner, function=name, target=receiver, lines=rows, sites=len(rows))


locations = [
    call_count('experiments/h1_selector_parent_controller_development_v2.py', 'Parent', '_source', 'preparation.prepare'),
    call_count('experiments/h1_selector_parent_controller_development_v2.py', 'Parent', '_source', 'preparation.bind'),
    call_count('experiments/h1_selector_launch_preparation_development_v2.py', None, 'prepare', 'worker.request_document'),
    call_count('experiments/h1_selector_launch_preparation_development_v2.py', None, 'bind', 'prepare_fixed'),
    call_count('experiments/h1_selector_released_worker_development_v2.py', None, 'request_document', 'snapshot.rebuild'),
    call_count('experiments/h1_selector_worker_output_inspection_development_v2.py', None, '_inspect', '_source'),
    call_count('experiments/h1_selector_worker_output_inspection_development_v2.py', None, '_source', 'snapshot.rebuild'),
    call_count('experiments/h1_selector_input_snapshot_development_v2.py', None, 'rebuild', '_build'),
    call_count('experiments/h1_selector_input_snapshot_development_v2.py', None, '_build', 'phase._fresh'),
    call_count('experiments/h1_phase_exact_source_current_development_v2.py', None, '_prepare', '_replay'),
    call_count('experiments/h1_phase_exact_source_current_development_v2.py', None, '_prepare', 'registry.prepare'),
    call_count('experiments/h1_phase_historical_controller_development_v1.py', None, '_observe_sources', '_source_paths'),
]
counts = [row['sites'] for row in locations]
assert counts[:11] == [1, 1, 2, 2, 1, 2, 1, 2, 1, 2, 2]
source_rebuilds = (counts[0] + counts[1] * counts[3]) * counts[2] * counts[4]
inspection_rebuilds = counts[5] * counts[6]
rebuilds = source_rebuilds + inspection_rebuilds
source_prepares = rebuilds * counts[7] * counts[8]
# Prefix's required successful counter assertion is checked, not inferred from
# a loop in the hour inspector. Each full prefix has two full and two fresh.
prefix_file = REPO / 'experiments/h1_historical_n0_verifier_development_v1.py'
prefix_ast = ast.parse(prefix_file.read_bytes())
assert any(isinstance(n, ast.Compare) and ast.unparse(n) == '(scope.full_calls, scope.revalidation_calls) != (2, 2)'
    for n in ast.walk(prefix_ast))
per_source_full = counts[9] * 2
per_retained = dict(snapshot_rebuilds=rebuilds, source_prepares=source_prepares,
    full_n0_hour_audits=source_prepares*per_source_full,
    fresh_n0_hour_revalidations=source_prepares*per_source_full,
    registry_preparations=source_prepares*counts[10],
    registry_loads=source_prepares*counts[10]*2,
    source_window_loads=source_prepares*8)
# The Handoff multiplicity is an independently inspected conditional call DAG,
# not dynamic execution evidence and not a generic Python control-flow solver.
retained = 13*4 + 4*2 + (13*3 + 3*2)*2
assert retained == 150 and per_retained['full_n0_hour_audits'] == 64

plan = read('parent_inspection_footprint_plan_04.json')
old = read('parent_inspection_footprint_monitor_03/terminal.json')
outer = read('parent_inspection_footprint_monitor_04/terminal.json')
inner = read('parent_inspection_footprint_04_non_authoritative/terminal.json')
prefix = read('parent_inspection_footprint_04_non_authoritative/observed_open_prefix.json')
assert old['stop_reason'] == 'wall' and old['exit_code'] == 1
assert outer['exit_code'] == inner['exit_code'] == 1 and outer['stop_reason'] is None
assert 'planned diagnostic prefix elapsed' in inner['error'] and 'cleanup_error' not in inner
assert inner['diagnostic_code_and_path_cleanup_verified']
assert prefix['sampler_receipt']['sampler_stopped'] and not prefix['sampler_receipt']['errors']
assert not prefix['sampler_receipt']['join_errors']
for result in (old, outer):
    assert result['source_unchanged'] and result['saved_files_unchanged'] and result['old_chain_unchanged']
    assert result['observed_owned_processes_absent'] and not result['observed_owned_processes_remaining']
    assert not result['errors']
for name, pin in {**plan['source_sha256'], **plan['old_chain_sha256'], **plan['saved_sha256']}.items():
    assert sha256(Path(name).read_bytes()).hexdigest() == pin, name
samples = [json.loads(row) for row in (HERE / 'parent_inspection_footprint_04_non_authoritative/python_stack_samples.jsonl').read_text(encoding='utf-8').splitlines()]


def frames(file, function):
    return sum(any(Path(f['file']).name == file and f['function'] == function for f in row['frames']) for row in samples)


lock_opens = [row for row in prefix['rows'] if Path(row['path']).suffix == '.lock']
assert len(lock_opens) == 1 and lock_opens[0]['calls'] == 7 and lock_opens[0]['modes'] == ['r']
value = dict(schema='h1_parent_bottleneck_postcheck_development_v1', exit_code=0,
    scope='static call-DAG and incomplete bounded-prefix evidence reconciliation',
    runtime_optimization_implemented=False, full_hour0_chain_passed=False,
    formal_result=False, resource_admission=False, native_execution_authorized=False,
    call_sites=locations, successful_three_actual_handoff_retained_boundaries=retained,
    retained_multiplicity=dict(direct_bundle_validate=13*4, direct_records=4*2,
        recursive_reference=(13*3+3*2)*2),
    counts_are_static_conditional_success_path=True,
    full_per_retained=per_retained,
    full_handoff_retained_subgraph={key:value*retained for key,value in per_retained.items()},
    excluded_paths=['four standalone records snapshot rebuilds and sequence inspections',
        'common calls', 'initial producer runs', 'close/reopen independent replay',
        'negative tests', 'other Handoff correspondence checks'],
    prefix_observation=dict(seconds=prefix['elapsed_seconds'], samples=len(samples),
        inspection_source_samples=frames('h1_selector_worker_output_inspection_development_v2.py','_source'),
        phase_fresh_samples=frames('h1_phase_owner_development_v2.py','_fresh'),
        numeric_hour_inspect_samples=frames('h1_timed_hour_development_v1.py','inspect'),
        open_events=sum(row['calls'] for row in prefix['rows']), open_paths=len(prefix['rows']),
        not_wall_time_share=True, complete_dependency_closure_proven=False),
    lock_read_erratum=dict(original_terminal_bytes_preserved=True,
        claim_requiring_correction='externally_owned_input_locks_not_touched must not mean no read-only opens',
        read_only_lock_opens_observed=lock_opens,
        original_readers_do_not_acquire_writer_byte_range_lock=True,
        no_lock_write_or_acquisition_claim_scope='static original reader paths; outer monitor acquires no input locks',
        unchanged_lock_access_time_not_claimed=True,
        incomplete_03_open_footprint_does_not_prove_no_lock_opens=True),
    closure_assessment=dict(whole_parent_cache_admitted=False,
        historical_source_paths_alone_sufficient=False,
        bootstrap_970_file_phase_inventory_on_this_route=False,
        prefix_scope_result_reuse_across_closed_nonce_admitted=False,
        next_boundary='versioned source reconstruction with explicit ordered dependency closure and active execution receipt'),
    code_and_input_cleanup_verified=True,
    evidence_sha256={str(HERE/name):sha256((HERE/name).read_bytes()).hexdigest() for name in (
        'parent_inspection_footprint_plan_04.json',
        'parent_inspection_footprint_monitor_03/terminal.json',
        'parent_inspection_footprint_monitor_04/terminal.json',
        'parent_inspection_footprint_04_non_authoritative/terminal.json',
        'parent_inspection_footprint_04_non_authoritative/observed_open_prefix.json')},
    source_sha256={str(REPO/row['file']):sha256((REPO/row['file']).read_bytes()).hexdigest() for row in locations})
target = OUT / 'terminal.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(value, stream, indent=2)
print(json.dumps(dict(exit_code=0, retained_boundaries=retained,
    full_n0_hour_audits=value['full_handoff_retained_subgraph']['full_n0_hour_audits'],
    source_window_loads=value['full_handoff_retained_subgraph']['source_window_loads'],
    samples=len(samples), lock_read_erratum_recorded=True,
    full_hour0_chain_passed=False, formal_result=False)))
