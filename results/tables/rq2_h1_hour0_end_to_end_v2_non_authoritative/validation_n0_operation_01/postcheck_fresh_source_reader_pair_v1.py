"""Close the single fixed-order reader pair; never infer full-chain timing."""
from hashlib import sha256
import json
from pathlib import Path
import traceback

import psutil

HERE = Path(__file__).resolve().parent
PINS = {
    'fresh_source_reader_plan_04_baseline.json': 'b9709ce6fbbb99db945a3d36db9aaf0df4bf073174c3df1d12430dff71145910',
    'fresh_source_reader_plan_04_candidate.json': 'f9ff06b4aef1956ceb5a218b2721d3cd21801b045d3bb3889a8fb7fdee2633aa',
    'source_reader_input_postcheck_plan_01.json': 'c84b0f1cd1b9bbf303d78e1dd19779fcd9989c70661967a047c4670b5028d288',
    'source_reader_input_postcheck_01_baseline_non_authoritative/terminal.json': '902a6e157254f4f88b4382cb903e2dddfc01a37e62174eba9ff67ddf03dc693a',
    'run_candidate_after_input_postcheck_v2.py': '929dec77d11e24b024e75ad8e69394fdd987dd9341427aa4044f46e9d152f6ec',
    'fresh_source_reader_monitor_04_baseline/terminal.json': 'f90d256b12ea2873b0d4dfe561b60e0cb6f6411814101e799bbdf970249c1cb4',
    'fresh_source_reader_monitor_04_candidate/terminal.json': 'e06802a5df29314bf2d2740ab77aa4aff4b5c0484f01c85ad1b2b2ce37a8c2ed',
}
OUT = HERE / 'fresh_source_reader_pair_postcheck_01_non_authoritative'
OUT.mkdir(exist_ok=False)
evidence = {}
result = dict(exit_code=1, formal_result=False, resource_admission=False,
              full_hour0_chain_passed=False, whole_workflow_performance_review_complete=False,
              independent_repetitions=0, fixed_order_pairs=1,
              baseline_transient_lock_ABA_observed=False)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read(path):
    evidence[str(path)] = digest(path)
    return json.loads(path.read_bytes())


try:
    for name, pin in PINS.items():
        if digest(HERE / name) != pin:
            raise ValueError('fixed pair evidence differs: ' + name)
    input_plan = read(HERE / 'source_reader_input_postcheck_plan_01.json')
    wrapper = read(HERE / 'candidate_after_input_postcheck_02_non_authoritative/terminal.json')
    assert wrapper['exit_code'] == 0 and not wrapper['errors'] and wrapper['stop_reason'] is None
    assert not wrapper['observed_owned_processes_remaining']
    assert wrapper['pre_input_postcheck_sha256'] == PINS['source_reader_input_postcheck_01_baseline_non_authoritative/terminal.json']
    assert wrapper['wrapper_sha256'] == PINS['run_candidate_after_input_postcheck_v2.py']
    plans = {}
    inners = {}
    receipts = {}
    for mode in ('baseline', 'candidate'):
        plan = plans[mode] = read(HERE / f'fresh_source_reader_plan_04_{mode}.json')
        outer = Path(plan['outer_output'])
        inner = Path(plan['inner_output'])
        request = read(outer / 'request.json')
        terminal = read(outer / 'terminal.json')
        inners[mode] = read(inner / 'terminal.json')
        assert {key: request.get(key) for key in plan} == plan
        assert request['plan_sha256'] == PINS[f'fresh_source_reader_plan_04_{mode}.json']
        assert terminal['exit_code'] == terminal['inner_exit_code'] == terminal['child_exit_code'] == 0
        assert not terminal['errors'] and terminal['stop_reason'] is None
        assert terminal['observed_owned_processes_absent'] and not terminal['process_observation_errors']
        assert digest(inner / 'terminal.json') == terminal['inner_terminal_sha256']
        if mode == 'candidate':
            assert wrapper['candidate_request_sha256'] == digest(outer / 'request.json')
            assert wrapper['candidate_terminal_sha256'] == digest(outer / 'terminal.json')
            assert request['baseline_admission']['baseline_terminal_sha256'] == PINS['fresh_source_reader_monitor_04_baseline/terminal.json']
        for key in ('source', 'saved', 'old_chain'):
            assert terminal[key + '_unchanged'] and not terminal[key + '_drift']
            for name, pin in plan[key + '_sha256'].items():
                assert digest(Path(name)) == pin, name
                if key == 'source':
                    path = Path(name)
                    repo = HERE.parents[3]
                    relative = path.relative_to(repo) if path.is_relative_to(repo) else Path('vendor') / path.relative_to(Path('D:/'))
                    assert digest(outer / 'tested_bytes' / relative) == pin, name
        for row in (*terminal['observed_owned_processes'], *plan['completed_input_owned_processes'], *wrapper['observed_owned_processes']):
            try:
                assert psutil.Process(row['pid']).create_time() != row['creation_time']
            except psutil.NoSuchProcess:
                pass
        post = read(HERE / f'source_reader_input_postcheck_01_{mode}_non_authoritative/terminal.json')
        assert post['exit_code'] == 0 and post['phase'] == mode and post['regular_input_files'] == 134
        assert post['relative_files_sha256'] == input_plan['relative_files_sha256']
        assert post['locked_and_released'] == input_plan['relative_locks']
        assert post['mode_terminal_sha256'] == digest(outer / 'terminal.json')
        assert post['plan_sha256'] == PINS['source_reader_input_postcheck_plan_01.json']
        receipt = receipts[mode] = read(inner / 'bounded_read_receipt.json')
        closed = read(inner / 'bounded_closed_receipt.json')
        assert receipt['first_failure'] is None and not receipt['source_or_result_cache']
        assert closed['code_owner_closed'] and closed['path_open_restored'] and closed['path_read_bytes_restored']
        assert not any(closed[k] for k in ('remaining_code_handles', 'remaining_streams', 'remaining_proxies', 'cleanup_errors'))
        assert read(inner / 'path_closed_receipt.json') == dict(dispatch_restored=True, state='closed', remaining_directory_handles=0, remaining_paths=0)
        path_receipt = read(inner / 'path_receipt.json')
        assert path_receipt['leaf_lstat_fresh'] and not path_receipt['file_bytes_cached']
        metadata = read(inner / 'metadata_receipt.json')
        assert metadata['misses'] == 0 and metadata['discovery_windows'] == 1 and not metadata['distribution_discovery_cached']
        bookends = read(inner / 'identity_bookends.json')
        assert bookends['test_only_identity_cache'] and not bookends['source_identity_cache']
        assert all(row['before'] == row['after'] for row in bookends['identities'].values())
        admitted = read(inner / 'fixture_path_admitted.json')
        assert admitted['paths'] == admitted['configured_paths']
        assert all(count == 1 for count in admitted['root_duplicate_counts'].values())
    for key in ('source_sha256', 'saved_sha256', 'old_chain_sha256', 'code_lease_sha256', 'fixture_base', 'path_roots'):
        assert plans['baseline'][key] == plans['candidate'][key]
    for name in ('baseline.json', 'baseline_complete_source_projection.json', 'path_receipt.json', 'metadata_receipt.json', 'identity_bookends.json'):
        left = read(Path(plans['baseline']['inner_output']) / name)
        right = read(Path(plans['candidate']['inner_output']) / name)
        if name == 'baseline.json':
            left.pop('seconds'); right.pop('seconds')
        assert left == right, name
    for key in ('exact_stable_read_calls', 'exact_stable_read_attempts', 'failed_underlying_reads',
                'original_requested_bytes', 'actual_requested_bytes', 'fallback_opens'):
        assert receipts['baseline'][key] == receipts['candidate'][key]
    unit = read(HERE / 'bounded_entry_v3_monitor_unit_07/terminal.json')
    unit_request = read(HERE / 'bounded_entry_v3_monitor_unit_07/request.json')
    assert unit['exit_code'] == 0 and unit['source_unchanged']
    entry = HERE / 'bounded_stable_read_entry_v3.py'
    assert unit_request['source_sha256'][str(entry)] == digest(entry)
    before = inners['baseline']['source_seconds']
    after = inners['candidate']['source_seconds']
    reduction = (before - after) / before
    result.update(exit_code=0, baseline_source_seconds=before, candidate_source_seconds=after,
                  source_wall_reduction_fraction=reduction, required_reduction_fraction=0.05,
                  candidate_adopted=reduction >= 0.05,
                  decision='ADOPT_DRAFT_READER' if reduction >= 0.05 else 'STOP_BRANCH_RETAIN_V2',
                  complete_source_fields_equal=True, original_scientific_io_counts_equal=True,
                  fixed_134_file_input_postchecks_passed=True, ten_locks_released=True,
                  note='One ordered pair; no statistical or whole-chain speedup claim.')
except BaseException:
    result['error'] = traceback.format_exc()
result['evidence_sha256'] = evidence
result['postchecker_sha256'] = digest(Path(__file__))
with (OUT / 'terminal.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps({key: value for key, value in result.items() if key != 'evidence_sha256'}))
raise SystemExit(result['exit_code'])
