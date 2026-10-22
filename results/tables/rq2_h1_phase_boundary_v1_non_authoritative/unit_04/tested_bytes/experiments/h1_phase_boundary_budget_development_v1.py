"""Read-only cost and evidence audit for the finite H1 phase boundary.

Counts describe the existing v2 owner, with no alternate witness or recovery.
They are work units, never a wall-time prediction or execution authority.
"""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
PRIOR = ROOT / 'results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative'


def schedule(hours, *, terminal=False, public_inspect=False, missing_next=False):
    if type(hours) is not int or not 1 <= hours <= 192:
        raise ValueError('completed hours must be 1..192')
    if terminal and missing_next or missing_next and hours == 192:
        raise ValueError('missing-needed-source and resolved terminal are different paths')
    # Each tuple is (operation, accepted N prefix length, selected currents).
    batches = [('create', 1, 1)]
    for h in range(hours):
        batches.extend((('ready', max(1, h), max(1, h)),
                        ('current', h + 1, 1), ('pre_paired', h + 1, 1),
                        ('post_paired', h + 1, h + 1)))
    if missing_next:
        # Ready succeeds; the next normal/source attempt fails before a new N.
        batches.append(('missing_ready', hours, hours))
    if terminal:
        batches.extend((('terminal_ready', hours, hours),
                        ('terminal_post', hours, hours)))
    batches.append(('reopen_constructor', hours, hours))
    if public_inspect:
        batches.append(('public_inspect', hours, hours))
    return dict(
        hours=hours, terminal=terminal, missing_next=missing_next,
        public_inspect=public_inspect, batch_calls=len(batches),
        reader_observations=2 * len(batches),
        reader_prefix_hour_weight=2 * sum(h for _, h, _ in batches),
        parent_inspect_traversals=4 * len(batches),
        parent_inspect_prefix_hour_weight=4 * sum(h for _, h, _ in batches),
        materialized_currents=sum(n for _, _, n in batches),
        registry_prepare_calls_for_materialization=2 * sum(n for _, _, n in batches),
        paired_outcomes=hours, minimum_events=3 * hours - (0 if terminal else 1),
        operations=dict(Counter(name for name, _, _ in batches)),
        excludes_independent_historical_snapshot_anchor_and_normal_internals=True)


def business_history_lower_bound(hours, lanes):
    """Only ready + post-paired full owner replay; all lanes stay paired/active.

At an h-outcome prefix, prepare/post-assess contribute h**2 per lane;
intent/attempt assessments and the final assessment contribute another h**2.
cursor validation, serialization, live branches and terminal tails add work.
"""
    if type(hours) is not int or not 1 <= hours <= 192 or type(lanes) is not int or lanes < 1:
        raise ValueError('bounded hours and positive lane count required')
    return 2 * lanes * sum(h * h + (h + 1) * (h + 1) for h in range(hours))


def _hash(path):
    return sha256(path.read_bytes()).hexdigest()


def verify_map(pins):
    bad = []
    for name, expected in pins.items():
        path = Path(name)
        if not path.is_absolute():
            path = ROOT / path
        if not path.is_file() or _hash(path) != expected:
            bad.append(name)
    return dict(count=len(pins), mismatches=bad)


def audit():
    request = json.loads((PRIOR / 'connected_03/request.json').read_bytes())
    post = json.loads((PRIOR / 'connected_03_postcheck.json').read_bytes())
    final = json.loads((PRIOR / 'final_verification_03.json').read_bytes())
    acceptance = json.loads((PRIOR / 'development_acceptance.json').read_bytes())
    case = Path(request['base']) / 'test_three_hour_connected_outa0'
    result = json.loads((case / 'outage_chain_result.json').read_bytes())
    current = verify_map(request['sources_sha256'])
    inherited = verify_map(post['inherited_source_sha256'])
    saved = verify_map(result['saved_files_sha256'])
    bound_reports = verify_map(final['bindings'])
    bound_acceptance = verify_map(acceptance['bindings'])
    case_inventory = verify_map(post['diagnostic_case_files_sha256'])
    if any(item['mismatches'] for item in
           (current, inherited, saved, bound_reports, bound_acceptance, case_inventory)):
        raise ValueError('prior evidence has changed; do not reuse it')
    counted = schedule(3, missing_next=True, public_inspect=True)
    assert (counted['reader_observations'], counted['reader_prefix_hour_weight'],
            counted['parent_inspect_traversals'], counted['parent_inspect_prefix_hour_weight']) == (32, 64, 64, 128)
    assert len(result['batch_observations']) == counted['reader_observations']
    assert sum(v['completed_hours'] for v in result['batch_observations']) == counted['reader_prefix_hour_weight']
    targets = {}
    for hours in (168, 170, 192):
        row = schedule(hours, terminal=True, public_inspect=True)
        row.update(
            normal_fake_jobs=hours, toy_normal_stages=5 * hours,
            toy_selector_capture_upper_bound_three_active_lanes=13 * hours,
            toy_normal_job_deadline_sum_seconds=240 * hours,
            toy_selector_solver_allowance_sum_seconds=13 * hours,
            business_history_length_lower_bound_three_active_lanes=business_history_lower_bound(hours, 3),
            existing_fixture_event_cap=32, event_cap_covers_target=False,
            wall_prediction_seconds=None, total_wall_admission_seconds=None,
            target_peak_rss_bytes=None, target_storage_bytes=None)
        targets[str(hours)] = row
    paths = [
        Path(__file__), ROOT / 'agent.md', ROOT / 'AGENTS.md',
        ROOT / 'experiments/h1_cross_hour_owner_development_v2.py',
        ROOT / 'experiments/h1_phase_owner_development_v1.py',
        ROOT / 'experiments/h1_exact_business_development_v1.py',
        ROOT / 'experiments/h1_finite_followup_assessment_development_v1.py',
        ROOT / 'experiments/h1_phase_exact_source_batch_development_v1.py',
        ROOT / 'experiments/h1_phase_historical_batch_development_v1.py',
        ROOT / 'tests/test_h1_cross_hour_owner_development_v1.py',
        ROOT / 'tests/h1_cross_hour_outage_fixture_v1.py',
        ROOT / 'tests/test_h1_finite_followup_assessment_development_v1.py',
        ROOT / 'configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml',
        ROOT / 'docs/model_spec/rq2_finite_mechanism_protocol_candidate_v2.md',
        PRIOR / 'workflow_performance_review_readable.md',
        PRIOR / 'connected_03/request.json', PRIOR / 'connected_03_postcheck.json',
        PRIOR / 'final_verification_03.json', PRIOR / 'development_acceptance.json',
        case / 'outage_chain_result.json', case / 'external_preclose_checkpoint.json']
    return dict(
        status='DRAFT_NONAUTHORITATIVE',
        scope='existing_v2_connected_path_cost_audit_and_admission_rejection',
        environment=dict(python=sys.version, executable=sys.executable, platform=platform.platform()),
        reused_evidence=dict(current_source=current, inherited_source=inherited,
                             owned_files=saved, final_reports=bound_reports,
                             acceptance=bound_acceptance, complete_case_inventory=case_inventory,
                             connected03_counts_reproduced=counted),
        target_work_units=targets,
        existing_fixture_first_rejected_next_relative_hour=10,
        existing_fixture_maximum_completed_hours_with_terminal_by_event_count_only=10,
        formal_RTS_normal_stage_slots_at_192_hours=232 * 192,
        formal_RTS_stage_slots_are_not_toy_measurements=True,
        blockers=[
            '32-event toy manifest fails before the eleventh paired hour; separate full-horizon resource bounds required',
            'source prefix work is quadratic and nested business history validation is at least cubic',
            '192h source/normal/history/serialization/failure/terminal wall and RSS/storage lack representative evidence',
            'unobserved dynamic dependency closure/freshness is unproved for cross-operation caching',
            'missing-needed-followup retains a pending attempt, without a typed right-censoring terminal',
            'normal writer cannot adopt a closed saved root for further production'],
        overall_performance_review_complete=False, long_connected_launch_admitted=False,
        resource_admission=False, formal_execution_ready=False,
        native_execution_authorized=False, real_native_calls=0, new_normal_jobs=0,
        full_192_hour_execution_verified=False, formal_result=False,
        bindings={str(p): _hash(p) for p in paths})


if __name__ == '__main__':
    destination = Path(sys.argv[1])
    report = audit()
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(output=str(destination), source_pins=report['reused_evidence']['current_source']['count'],
                          owned_files=report['reused_evidence']['owned_files']['count'],
                          long_connected_launch_admitted=False)))
