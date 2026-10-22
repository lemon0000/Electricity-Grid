"""Verify the bounded source-cost diagnostic and reuse prior evidence by SHA."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import platform
import re
import sys

import psutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TABLES = REPO / 'results/tables'
OUTAGE = TABLES / 'rq2_h1_cross_hour_outage_v1_non_authoritative'
PHASE = TABLES / 'rq2_h1_phase_boundary_v1_non_authoritative'
RECORD = TABLES / 'rq2_h1_business_record_replay_v1_non_authoritative'
CASE = Path('D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0')


def read(path):
    return json.loads(Path(path).read_bytes())


def pin(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def current(mapping):
    assert all(pin(path) == expected for path, expected in mapping.items())
    return len(mapping)


def main():
    destination = HERE / (sys.argv[1] if len(sys.argv) == 2 else 'development_acceptance_v1.json')
    if destination.parent != HERE or not destination.name.startswith('development_acceptance_v'):
        raise ValueError('local versioned output required')
    if destination.exists():
        raise ValueError('fresh diagnostic verification output required')
    terminal = read(HERE / 'profile_02/terminal.json')
    request = read(HERE / 'profile_02/request.json')
    worker = read(HERE / 'profile_02/reader_terminal.json')
    assert terminal['exit_code'] == worker['exit_code'] == 0 and terminal['reader_accepted']
    assert terminal['reader'] == worker and terminal['reason'] is None and not terminal.get('error')
    assert not terminal['changed_sources'] and not terminal['cleanup_events']
    assert not terminal['observed_processes_remaining']
    assert terminal['outer_seconds'] <= request['wall_cap_seconds'] == 180
    assert terminal['peak_sampled_tree_rss_bytes'] <= request['sampled_tree_rss_cap_bytes'] == 1024 ** 3
    assert terminal['peak_logical_bytes'] <= request['logical_storage_cap_bytes'] == 128 * 1024 ** 2
    pins = current(request['sources_sha256'])
    assert pins == 1302
    for path in (HERE / 'profile_02/tested_bytes').rglob('*'):
        if path.is_file():
            live = REPO / path.relative_to(HERE / 'profile_02/tested_bytes')
            assert pin(path) == pin(live) == request['sources_sha256'][str(live)]
    assert worker['metric']['completed_hours'] == 3 and worker['metric']['selected_hours'] == [0, 1, 2]
    assert worker['metric']['parent_inspect_traversals'] == 2
    assert worker['call_counts'] == dict(inspect_job=12, timed_stage_inspect=60)
    assert worker['saved_case_files'] == 465 and worker['saved_case_bytes_unchanged']
    assert worker['saved_normal_audits_equal'] and len(worker['captured_audits']) == 3
    assert worker['audit'] == dict(old_case_read_opens=21291, rejected_mutations=0)
    assert worker['Jobs'] == worker['real_native_calls'] == 0 and not worker['formal_result']
    assert worker['cprofile_overhead_included'] and not worker['optimization_implemented']
    assert not worker['complete_dynamic_closure_proved'] and not worker['unobserved_ABA_covered']
    functions = read(HERE / 'profile_02/profile_functions.json')
    focus = [row for row in functions if row['function'] in ('_dependencies', 'normal_input_identity')
             and row['file'].endswith('continuous_grid_normal.py')]
    assert len(focus) == 2 and all(row['calls'] == 1560 for row in focus)
    versions = [row for row in functions if row['function'] == 'version' and row['line'] == 882 and 'importlib' in row['file']]
    assert len(versions) == 1 and versions[0]['calls'] == 10922
    edges = [row for row in read(HERE / 'profile_02/profile_call_edges.json')
             if row['callee'] == 'inspect' and row['callee_file'].endswith('h1_phase_historical_batch_development_v1.py')]
    assert len(edges) == 2 and {row['caller'] for row in edges} == {'__init__', 'replay_prefixes'}
    assert all(row['counts'][:2] == [1, 1] for row in edges)
    fixture = read(HERE / 'profile_02/static_identity_bookends.json')
    assert len(fixture['functions']) == 15 and not fixture['errors']
    assert all(row['original_callable_restored'] for row in fixture['functions'])
    assert sum(row['calls'] for row in fixture['functions']) == 4676
    assert sum(row['original_computations'] for row in fixture['functions']) == 5
    failed = read(HERE / 'profile_01/terminal.json')
    assert failed['exit_code'] == 1 and failed['error'] and not failed['observed_processes_remaining']
    assert 'open_manifest' in (HERE / 'profile_01/error.txt').read_text(encoding='utf-8')
    assert 'pstats' in (HERE / 'profile_01/stderr.txt').read_text(encoding='utf-8')
    assert not (HERE / 'profile_01/reader_terminal.json').exists()
    previous_pins = read(HERE / 'profile_01/request.json')['sources_sha256']
    historical_failed = []
    for path, expected in previous_pins.items():
        target = Path(path)
        if pin(path) != expected:
            target = HERE / 'profile_01/tested_bytes' / target.relative_to(REPO)
            historical_failed.append(dict(path=path, retained_snapshot=str(target), sha256=expected))
        assert pin(target) == expected
    assert {Path(row['path']).name for row in historical_failed} == {'profile_saved_v1.py', 'design_and_budget.md'}
    old = read(OUTAGE / 'connected_03_postcheck.json')
    inventory = {str(path): pin(path) for path in CASE.rglob('*') if path.is_file()}
    assert inventory == old['diagnostic_case_files_sha256']
    counts = dict(case_files=len(inventory), inherited_source_pins=current(old['inherited_source_sha256']),
        connected_source_pins=current(read(OUTAGE / 'connected_03/request.json')['sources_sha256']),
        connected_postcheck_bindings=current(old['bindings']),
        owned_files=current(read(CASE / 'outage_chain_result.json')['saved_files_sha256']))
    assert counts == dict(case_files=465, inherited_source_pins=1279, connected_source_pins=1299,
                          connected_postcheck_bindings=21, owned_files=444)
    snapshot_map = {}
    for folder in (PHASE, RECORD, HERE):
        for row in read(folder / 'canonical_doc_updates.json')['updates']:
            assert pin(row['before_snapshot']) == row['before_sha256']
            snapshot_map[(row['path'], row['before_sha256'])] = row['before_snapshot']
    canonical_updates = read(HERE / 'canonical_doc_updates.json')['updates']
    for row in canonical_updates:
        before, after = Path(row['before_snapshot']).read_bytes(), Path(row['path']).read_bytes()
        offset, length = row['insertion_offset'], row['insertion_length']
        assert pin(row['path']) == row['after_sha256']
        assert after[:offset] + after[offset + length:] == before
    reused = []
    for path in (RECORD / 'development_acceptance_v2.json', RECORD / 'final_verification.json',
                 PHASE / 'development_acceptance_v2.json', PHASE / 'final_verification.json'):
        artifact = read(path)
        historical = []
        for name, expected in artifact['bindings'].items():
            target = name if pin(name) == expected else snapshot_map[(name, expected)]
            assert pin(target) == expected
            if target != name:
                historical.append(dict(path=name, retained_snapshot=target, sha256=expected))
        reused.append(dict(path=str(path), sha256=pin(path), verified_bindings=len(artifact['bindings']),
                           historical_canonical_bindings=historical))
    guards = []
    for row in read(PHASE / 'reused_guard_evidence.json')['records']:
        path = REPO / row['path']
        assert pin(path) == row['sha256']
        guards.append(dict(path=str(path), verified_pins=current(read(path)[row['pin_field']])))
    work = read(HERE / 'call_dag_and_work_units.json')
    current(work['bindings'])
    for horizon, readers, weight in (('168', 1354, 114580), ('192', 1546, 149380)):
        row = work['target_work_units'][horizon]
        assert row['reader_observations'] == readers and row['reader_prefix_hour_weight'] == weight
        assert row['current_inspect_job_calls'] == 4 * weight and row['current_toy_M5_stage_inspect_calls'] == 20 * weight
        assert row['current_parent_inspect_traversals'] == 2 * readers
        candidate = row['conditional_constructor_reuse']
        assert not candidate['implemented'] and not candidate['independently_validated']
        assert candidate['inspect_job_calls'] == 2 * weight and candidate['toy_M5_stage_inspect_calls'] == 10 * weight
    remaining = []
    for label in ('profile_01', 'profile_02'):
        for pid, created in read(HERE / label / 'terminal.json')['observed_processes'].items():
            try:
                process = psutil.Process(int(pid))
                if process.create_time() == created and process.is_running():
                    remaining.append(dict(pid=int(pid), create_time=created))
            except psutil.NoSuchProcess:
                pass
    assert not remaining
    preceding = None
    if destination.name != 'development_acceptance_v1.json':
        previous = read(HERE / 'development_acceptance_v1.json')
        retained = read(HERE / 'preseal_review_01_snapshots.json')['snapshots']
        lookup = {(row['path'], row['sha256']): row['retained_snapshot'] for row in retained}
        historical = []
        for path, expected in previous['bindings'].items():
            target = path if pin(path) == expected else lookup[(path, expected)]
            assert pin(target) == expected
            if target != path:
                historical.append(dict(path=path, retained_snapshot=target, sha256=expected))
        preceding = dict(path=str(HERE / 'development_acceptance_v1.json'),
            sha256=pin(HERE / 'development_acceptance_v1.json'), verified_bindings=len(previous['bindings']),
            historical_bindings=historical)
    parsed = []
    for path in HERE.glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'))
        parsed.append(str(path))
    links = []
    for path in HERE.glob('*.md'):
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            link = path.parent / target.split('#', 1)[0]
            assert link.is_file()
            links.append(dict(document=str(path), target=str(link.resolve())))
    paths = {path for path in HERE.rglob('*') if path.is_file()}
    paths.update(Path(row['path']) for row in canonical_updates)
    paths.update(Path(row['path']) for row in reused)
    paths.update((OUTAGE / 'connected_03_postcheck.json', PHASE / 'budget_audit_v1.json'))
    report = dict(status='DRAFT_NONAUTHORITATIVE', scope='one_saved_three_hour_reader_cost_and_call_dag',
        current_source_pins=pins, reader_metric=worker['metric'], profile_script_elapsed_seconds=worker['elapsed_seconds'],
        outer_seconds=terminal['outer_seconds'], peak_sampled_tree_rss_bytes=terminal['peak_sampled_tree_rss_bytes'],
        peak_logical_bytes=terminal['peak_logical_bytes'], measured_call_counts=worker['call_counts'],
        dependency_focus=focus + versions, inspection_caller_edges=edges,
        saved_normal_audits_equal=True, inherited_evidence=counts,
        reused_prior_reports=reused, guard_pins_freshly_verified=guards,
        preceding_diagnostic_core_preserved=preceding,
        failed_setup_attempt_preserved=True, failed_attempt_current_vs_snapshot=historical_failed,
        canonical_prior_dirty_bytes_recoverable=True, syntax_parsed=parsed, local_markdown_links=links,
        observed_owned_pid_creation_pairs_remaining=remaining, complete_unobserved_process_tree_proof=False,
        environment=dict(executable=sys.executable, python=sys.version, platform=platform.platform(), psutil=psutil.__version__),
        constructor_successor_design_only=True, optimization_implemented=False, optimization_adopted=False,
        overall_performance_review_complete=False, long_connected_launch_admitted=False,
        total_192h_wall_prediction_seconds=None, total_192h_wall_admission_seconds=None,
        real_phase_terminal_reopen_verified=False, typed_followup_right_censor_terminal_verified=False,
        full_192_hour_execution_verified=False, complete_dynamic_closure_proved=False, unobserved_ABA_covered=False,
        resource_admission=False, native_execution_authorized=False, formal_execution_ready=False, formal_result=False,
        sealed=False, official_review_pass=False, real_native_calls=0, new_normal_jobs=0,
        bindings={str(path): pin(path) for path in sorted(paths)})
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(path=str(destination), sha256=pin(destination), bindings=len(report['bindings']),
                         profile_source_pins=pins, reused=counts, remaining_processes=remaining)))


if __name__ == '__main__':
    main()
