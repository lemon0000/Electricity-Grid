"""Verify saved executed bytes, current draft, prior evidence and process tails."""
from hashlib import sha256
import json
import os
from pathlib import Path

import psutil

import postcheck_v1 as post

HERE, REPO, PRIOR = post.HERE, post.REPO, post.PRIOR


def main():
    core_path = HERE / 'development_acceptance_v1.json'
    core = post.load(core_path)
    assert all(post.pin(name) == expected for name, expected in core['bindings'].items())
    state = post.load(HERE / 'formal_preparation_state_v4.json')
    assert len(state['gates']) == 16 and all(g['complete'] is False for g in state['gates'])
    assert all(post.pin(name) == expected for name, expected in state['bindings'].items())
    replay = post.load(HERE / 'status_builder_replay_verification.json')
    assert replay['exit_code'] == 0 and replay['before_sha256'] == replay['after_sha256']
    assert replay['builder_sha256'] == post.pin(HERE / 'build_status_v1.py')
    assert all(post.pin(HERE / name) == expected for name, expected in replay['after_sha256'].items())
    labels = ('probe_01', 'model_units_01', 'model_units_02', 'probe_02',
              'oracle_01', 'short_comparison_01', 'runtime_probe_01')
    receipts = {}
    remaining = []
    snapshots = [HERE / 'before_edit', HERE / 'canonical_before', PRIOR / 'canonical_before']
    for label in labels:
        root = HERE / label
        request, terminal = post.load(root / 'request.json'), post.load(root / 'terminal.json')
        assert terminal['exit_code'] == 0 and terminal['reason'] is None and not terminal.get('error')
        assert terminal['changed_sources'] == terminal['observed_processes_remaining'] == []
        assert terminal['new_normal_jobs'] == terminal['real_native_calls'] == 0
        resolved = post.resolve(request['sources_sha256'], [root / 'tested_bytes', *snapshots])
        verified_snapshots = {}
        for path in (root / 'tested_bytes').rglob('*'):
            if not path.is_file():
                continue
            original = REPO / path.relative_to(root / 'tested_bytes')
            expected = request['sources_sha256'][str(original)]
            assert post.pin(path) == expected
            verified_snapshots[str(path)] = expected
        for pid, created in terminal['observed_processes'].items():
            try:
                process = psutil.Process(int(pid))
                if process.create_time() == created and process.is_running():
                    remaining.append(int(pid))
            except psutil.NoSuchProcess:
                pass
        receipts[label] = dict(verified_pins=len(resolved),
            current_live_pins=sum(v['live'] for v in resolved.values()),
            preserved_snapshot_pins=sum(not v['live'] for v in resolved.values()),
            independently_read_tested_snapshot_count=len(verified_snapshots),
            tested_snapshot_sha256=verified_snapshots)
    runtime_runner = HERE / 'run_runtime_probe_v1.py'
    runtime_snapshot = HERE / 'runtime_probe_01/tested_bytes' / runtime_runner.relative_to(REPO)
    assert runtime_snapshot.read_bytes() == runtime_runner.read_bytes()
    correction = post.load(HERE / 'runtime_harness_provenance_correction_v1.json')
    assert correction['actual_executed_runner_sha256'] == post.pin(runtime_snapshot)
    prior_checks = {}
    for label, folder, expected_counts in (
        ('constructor', PRIOR, (157,164)),
        ('source_cost', HERE.parent / 'rq2_h1_source_replay_cost_v1_non_authoritative', (56,59))):
        final = post.load(folder / 'final_verification.json')
        assert post.pin(final['latest_core']) == final['latest_core_sha256']
        old_core = post.load(final['latest_core'])
        checked = [post.resolve(value['bindings'], snapshots) for value in (old_core, final)]
        assert tuple(len(v) for v in checked) == expected_counts
        prior_checks[label] = dict(core_bindings=len(checked[0]), final_bindings=len(checked[1]),
            core_sha256=final['latest_core_sha256'], final_sha256=post.pin(folder / 'final_verification.json'))
    for directory in ('status_before_review', 'status_before_idempotence_fix'):
        for row in post.load(HERE / directory / 'bindings.json')['files']:
            assert post.pin(row['preserved']) == row['sha256']
    before = post.load(HERE / 'before_edit_bindings.json')
    assert all(post.pin(row['preserved']) == row['sha256'] for row in before['files'])
    document_updates = post.load(HERE / 'canonical_doc_updates.json')['updates']
    assert len(document_updates) == 2
    for row in document_updates:
        current, original = Path(row['path']).read_bytes(), Path(row['before_snapshot']).read_bytes()
        offset, length = row['insertion_offset'], row['insertion_length']
        assert current[:offset]+current[offset+length:] == original
        assert sha256(original).hexdigest() == row['before_sha256'] and post.pin(row['path']) == row['after_sha256']
    case = Path('D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0')
    expected_case = post.load(REPO / 'results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03_postcheck.json')['diagnostic_case_files_sha256']
    assert {str(p): post.pin(p) for p in case.rglob('*') if p.is_file()} == expected_case
    owned = post.load(case / 'external_preclose_checkpoint.json')['saved_files_sha256']
    assert len(expected_case) == 465 and len(owned) == 444
    assert all(post.pin(name) == expected for name, expected in owned.items())
    related = []
    for process in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        if process.pid == os.getpid():
            continue
        try:
            info = process.info
            name = (info['name'] or '').lower()
            command = ' '.join(info['cmdline'] or [])
            if (name in ('python.exe', 'pythonw.exe') and 'h1_' in command
                    or name in ('gurobi_cl.exe', 'cplex.exe', 'ipopt.exe', 'highs.exe', 'scip.exe')):
                related.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    assert not remaining and not related
    assert all(post.pin(name) == expected for name, expected in core['bindings'].items())
    bindings = dict(core['bindings'])
    bindings[str(core_path)] = post.pin(core_path)
    result = dict(status='DRAFT_NONAUTHORITATIVE', latest_core=str(core_path),
        latest_core_sha256=post.pin(core_path), core_bindings_verified=len(core['bindings']),
        latest_state_bindings_verified=len(state['bindings']), open_preparation_gates=16,
        attempts=receipts, prior_evidence=prior_checks,
        runtime_actual_runner_and_tested_snapshot_bytes_equal=True,
        generated_template_and_actual_runner_provenance_separately_bound=True,
        both_status_draft_history_snapshots_verified=True, latest_status_builder_replay_bytes_identical=True,
        saved_case_files=465, saved_owned_files=444, saved_case_and_owned_sha256_unchanged=True,
        two_prior_dirty_canonical_documents_exact_bytes_preserved=True,
        whole_dirty_worktree_preservation_claimed=False,
        owned_observed_processes_remaining=remaining, active_related_processes=related,
        active_process_observation_scope='successfully_readable_processes_under_name_and_command_filter',
        complete_unobserved_process_tree_proof=False, independent_official_review_performed=False,
        objective_complete=False, overall_performance_review_complete=False,
        resource_admission=False, native_execution_authorized=False, formal_execution_ready=False,
        full_192_hour_execution_verified=False, sealed=False, formal_result=False,
        new_normal_jobs=0, real_native_calls=0, bindings=bindings)
    with (HERE / 'final_verification.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(core_bindings=len(core['bindings']), final_bindings=len(bindings),
        saved_files=465, owned_files=444, open_gates=16,
        tested_snapshots={k:v['independently_read_tested_snapshot_count'] for k,v in receipts.items()},
        active_related=related, final_sha256=post.pin(HERE / 'final_verification.json'), formal_result=False)))


if __name__ == '__main__':
    main()
