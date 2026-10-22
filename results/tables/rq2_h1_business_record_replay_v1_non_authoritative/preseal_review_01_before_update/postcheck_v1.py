"""Read-only artifact checks plus a fresh non-authoritative diagnostic report."""
import ast
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import re
import sys
import xml.etree.ElementTree as ET

import psutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PHASE = REPO / 'results/tables/rq2_h1_phase_boundary_v1_non_authoritative'
OUTAGE = REPO / 'results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative'


def read(path):
    return json.loads(Path(path).read_bytes())


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def verified(mapping):
    bad = [name for name, expected in mapping.items() if digest(name) != expected]
    assert not bad, bad
    return len(mapping)


def terminal(label, tests, expected_exit):
    folder = HERE / label
    request, result = read(folder / 'request.json'), read(folder / 'terminal.json')
    cases = ET.parse(folder / 'junit.xml').getroot().findall('.//testcase')
    assert len(cases) == tests and result['exit_code'] == expected_exit
    if expected_exit == 0:
        assert not any(case.findall('failure') + case.findall('error') + case.findall('skipped') for case in cases)
        assert result['junit']['accepted'] and result['all_expected_facts_retained']
        assert not result['changed_sources'] and not result.get('error')
        assert result['reason'] is None and not result['observed_processes_remaining']
        assert result['outer_seconds'] <= request['wall_cap_seconds']
        assert result['peak_sampled_tree_rss_bytes'] <= request['sampled_tree_rss_cap_bytes']
        assert result['peak_logical_bytes'] <= request['logical_storage_cap_bytes']
        pins = verified(request['sources_sha256'])
        for source in (folder / 'tested_bytes').rglob('*'):
            if source.is_file():
                live = REPO / source.relative_to(folder / 'tested_bytes')
                assert digest(source) == digest(live) == request['sources_sha256'][str(live)]
        for source, fact in result['facts'].items():
            assert digest(source) == digest(fact['retained_copy']) == fact['sha256']
    else:
        assert result['junit']['errors'] == 1 and not result['facts']
        assert 'ModuleNotFoundError' in (folder / 'stdout.txt').read_text(encoding='utf-8')
        # The single corrected profile script is historical at this attempt.
        # Its launch bytes are retained; do not claim they match current code.
        historical = 0
        for source in (folder / 'tested_bytes').rglob('*'):
            if source.is_file():
                live = REPO / source.relative_to(folder / 'tested_bytes')
                assert digest(source) == request['sources_sha256'][str(live)]
                historical += digest(source) != digest(live)
        assert historical == 1 and not result['observed_processes_remaining']
        pins = None
    return dict(tests=tests, exit_code=expected_exit, current_source_pins=pins,
        outer_seconds=result['outer_seconds'],
        peak_sampled_tree_rss_bytes=result['peak_sampled_tree_rss_bytes'],
        peak_logical_bytes=result['peak_logical_bytes'])


def main():
    destination = HERE / 'development_acceptance_v1.json'
    if destination.exists():
        raise ValueError('fresh diagnostic acceptance output required')
    units = terminal('unit_01', 22, 0)
    profile = terminal('profile_02', 1, 0)
    failed = terminal('profile_01', 1, 2)
    assert read(HERE / 'probe_01/terminal.json')['exit_code'] != 0
    plan = read(HERE / 'profile_plan_v1.json')
    assert plan['repeats_per_horizon'] == len(plan['orders']) == 2
    fact = read(HERE / 'profile_02/facts/profile_32.json')
    assert len(fact['rows']) == 12 and len(fact['scientific_payload_sha256']) == 33
    assert fact['scientific_payloads_unchanged'] and fact['original_and_successor_acceptance_equal']
    assert fact['new_normal_jobs'] == fact['real_native_calls'] == fact['phase_events_written'] == 0
    assert not fact['formal_result'] and not fact['paired_owner_authenticated']
    pairs = []
    for horizon in plan['horizons_business_hours']:
        for repeat in range(2):
            selected = [r for r in fact['rows'] if r['horizon'] == horizon and r['repeat'] == repeat]
            assert [r['path'] for r in selected] == plan['orders'][repeat]
            original, successor = ({r['path']: r for r in selected}[key] for key in ('original', 'successor'))
            for row in selected:
                assert row['validator_calls'] == 2 * (horizon + 1)
                assert row['original_record_replay_work_units'] == horizon * (horizon + 1)
            observation = successor['operation_observation']
            assert observation['records_observed'] == horizon * (horizon + 1)
            assert observation['original_record_replays'] == horizon and observation['record_reuses'] == horizon ** 2
            assert observation['cache_cleared'] and observation['closed_cleanly']
            assert not observation['active'] and not observation['poisoned']
            assert not observation['complete_dynamic_closure_proved'] and not observation['unobserved_ABA_covered']
            ratio = successor['total_validator_wall_seconds'] / original['total_validator_wall_seconds']
            assert ratio > 1
            pairs.append(dict(horizon=horizon, repeat=repeat, successor_to_original_wall_ratio=ratio))
    old_post = read(OUTAGE / 'connected_03_postcheck.json')
    reused = {field: verified(old_post[field]) for field in
              ('bindings', 'inherited_source_sha256', 'diagnostic_case_files_sha256')}
    reused['connected_launch_source_pins'] = verified(read(OUTAGE / 'connected_03/request.json')['sources_sha256'])
    case = Path('D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0')
    old_result = read(case / 'outage_chain_result.json')
    reused['saved_owned_files'] = verified(old_result['saved_files_sha256'])
    assert reused['inherited_source_sha256'] == 1279 and reused['diagnostic_case_files_sha256'] == 465
    assert reused['connected_launch_source_pins'] == 1299 and reused['saved_owned_files'] == 444
    observed = old_result['batch_observations']
    assert len(observed) == len({row['observation_token'] for row in observed}) == 32
    old_trace = [json.loads(line) for line in (case / 'cross_hour_timing.jsonl').read_bytes().splitlines()]
    timing = dict(reader_observations=32, reader_elapsed_sum_seconds=sum(row['seconds'] for row in observed),
        reader_max_seconds=max(row['seconds'] for row in observed),
        normal_wrapper_elapsed_sum_seconds=sum(seconds for name, seconds in old_result['owner_stage_timings'] if name == 'normal'),
        start_to_final_trace_seconds=old_trace[-1]['monotonic'] - old_trace[0]['monotonic'],
        measurements_nested_do_not_add_to_outer_wall=True)
    assert abs(timing['reader_elapsed_sum_seconds'] - 655.2262379) < 1e-6
    doc_updates = read(HERE / 'canonical_doc_updates.json')['updates']
    snapshots = {}
    for row in doc_updates:
        before, after = Path(row['before_snapshot']).read_bytes(), Path(row['path']).read_bytes()
        offset, count = row['insertion_offset'], row['insertion_length']
        assert sha256(before).hexdigest() == row['before_sha256']
        assert sha256(after).hexdigest() == row['after_sha256']
        assert after[:offset] + after[offset + count:] == before
        snapshots[(row['path'], row['before_sha256'])] = row['before_snapshot']
    prior_binding_checks = []
    for name in ('development_acceptance_v2.json', 'final_verification.json'):
        prior = read(PHASE / name)
        historical = []
        for path, expected in prior['bindings'].items():
            target = path if digest(path) == expected else snapshots[(path, expected)]
            assert digest(target) == expected
            if target != path:
                historical.append(dict(path=path, retained_snapshot=target, sha256=expected))
        prior_binding_checks.append(dict(artifact=str(PHASE / name), sha256=digest(PHASE / name),
            verified=len(prior['bindings']), historical_document_bindings=historical))
    verified(read(PHASE / 'budget_audit_v1.json')['bindings'])
    guard_checks = []
    for row in read(PHASE / 'reused_guard_evidence.json')['records']:
        path = REPO / row['path']
        assert digest(path) == row['sha256']
        guard_checks.append(dict(path=str(path), pins=verified(read(path)[row['pin_field']])))
    observed_remaining = []
    for label in ('unit_01', 'profile_01', 'profile_02'):
        for pid, created in read(HERE / label / 'terminal.json')['observed_processes'].items():
            try:
                process = psutil.Process(int(pid))
                if process.create_time() == created and process.is_running():
                    observed_remaining.append(dict(pid=int(pid), create_time=created))
            except psutil.NoSuchProcess:
                pass
    assert not observed_remaining
    parsed = []
    new_sources = [REPO / 'experiments/h1_business_record_replay_operation_development_v1.py',
                   REPO / 'tests/test_h1_business_record_replay_operation_development_v1.py']
    for path in new_sources + list(HERE.glob('*.py')):
        ast.parse(path.read_text(encoding='utf-8'))
        parsed.append(str(path))
    links = []
    for path in HERE.glob('*.md'):
        text = path.read_text(encoding='utf-8')
        for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)', text):
            assert '://' not in link
            target = path.parent / link.split('#', 1)[0]
            assert target.is_file(), target
            links.append(dict(document=str(path), target=str(target.resolve())))
    paths = set(new_sources + [Path(row['path']) for row in doc_updates])
    paths.update(path for path in HERE.rglob('*') if path.is_file())
    paths.update((PHASE / 'development_acceptance_v2.json', PHASE / 'final_verification.json',
                  PHASE / 'budget_audit_v1.json', OUTAGE / 'connected_03_postcheck.json',
                  case / 'outage_chain_result.json', case / 'cross_hour_timing.jsonl'))
    report = dict(status='DRAFT_NONAUTHORITATIVE', scope='detached_record_reuse_negative_performance_diagnostic',
        units=units, profile=profile, failed_profile_preserved=failed,
        failed_import_probe_preserved=True, original_and_successor_payloads_unchanged=True,
        paired_observations=pairs, optimization_adopted=False, owner_integration_performed=False,
        production_adoption_allowed=False, descriptive_diagnostic_only=True,
        inherited_evidence=reused, phase_prior_bindings=prior_binding_checks,
        original_guard_pins_freshly_verified=guard_checks, reused_nested_timings=timing,
        canonical_old_bytes_recoverable=True, historical_bindings_resolved_by_exact_snapshots=True,
        observed_owned_processes_remaining=observed_remaining, complete_unobserved_process_tree_proof=False,
        syntax_parsed=parsed, markdown_links_verified=links,
        environment=dict(executable=sys.executable, python=sys.version, platform=platform.platform(),
                         postcheck_pid=os.getpid(), psutil=psutil.__version__),
        new_normal_jobs=0, real_native_calls=0, formal_result=False, formal_execution_ready=False,
        resource_admission=False, native_execution_authorized=False, long_connected_launch_admitted=False,
        overall_performance_review_complete=False, total_192h_wall_prediction_seconds=None,
        full_192_hour_execution_verified=False, real_phase_terminal_reopen_verified=False,
        typed_followup_right_censor_terminal_verified=False, complete_dynamic_closure_proved=False,
        unobserved_ABA_covered=False, sealed=False, official_review_pass=False,
        bindings={str(path): digest(path) for path in sorted(paths)})
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(artifact=str(destination), sha256=digest(destination),
        bindings=len(report['bindings']), units=units, profile=profile,
        optimization_adopted=False, inherited_evidence=reused)))


if __name__ == '__main__':
    main()
