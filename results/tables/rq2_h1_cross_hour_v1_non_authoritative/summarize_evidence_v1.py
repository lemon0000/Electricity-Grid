"""Read-only numerical/artifact postcheck of a completed synthetic prefix."""
from collections import Counter, defaultdict
from contextlib import closing
from fractions import Fraction as Q
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import sys

HERE = Path(__file__).resolve().parent
label = sys.argv[1]
attempt = HERE/label
terminal = json.loads((attempt/'terminal.json').read_bytes())
assert terminal['exit_code'] == 0 and terminal['reason'] is None
assert terminal['source_unchanged'] and terminal['observed_processes_absent'] and not terminal['monitor_errors']
base = Path(terminal['retained_root'])
results = list(base.glob('test_*/cross_hour_result.json'))
assert len(results) == 1
case = results[0].parent
result = json.loads(results[0].read_bytes())
bookends = json.loads((case/'static_identity_bookends.json').read_bytes())
assert not bookends['errors'] and not bookends['dynamic_source_or_history_or_state_cached']
assert all(row['original_callable_restored'] for row in bookends['functions'])
for row in bookends['functions']:
    assert all(check['before'] == check['after'] for check in row['bookends'])
assert result['synthetic_hours'] == result['state']['hour'] == 2 and result['lanes'] == 3
assert result['normal_jobs'] == 2 and result['selector_stages'] == 18 and result['real_native_calls'] == 0
assert Counter(result['phase_fresh_hours']) == Counter({0:12, 1:4})
assert len({row['pid'] for row in result['normal_job_observations']}) == 2
assert all(row['exit_code'] == 0 and row['whole_job_quiescent'] for row in result['normal_job_observations'])
assert result['reopen_scientific_match'] and result['reopen_all_saved_bytes_match']
assert result['all_owned_lease_handles_closed'] and not result['formal_result']
assert not result['dynamic_source_or_history_or_state_cached']
assert not result['historical_reader_replaced'] and not result['phase_exact_source_prepare_replaced']
assert not result['exact_business_replaced'] and not result['numerical_replay_replaced']
roots = [case/name for name in ('normal_non_authoritative', 'owner_non_authoritative', 'holder_non_authoritative')]
assert {str(path) for root in roots for path in root.rglob('*') if path.is_file()} == set(result['saved_files_sha256'])
for name, pin in result['saved_files_sha256'].items():
    assert sha256(Path(name).read_bytes()).hexdigest() == pin


def events(path):
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=0)) as db:
        return [(seq, kind, json.loads(raw), head) for seq, kind, raw, head in
                db.execute('SELECT seq,kind,body,head FROM events ORDER BY seq')]


rows = events(case/'owner_non_authoritative/owner.sqlite')
assert [row[1] for row in rows] == ['intent', 'outcome', 'attempt', 'intent', 'outcome']
assert rows[-1][3] == result['outcome_head'] == result['registry_head']
projections = [row[2]['projection'] for row in rows if row[1] == 'outcome']
assert projections[-1]['after'] == result['state']
for projection in projections:
    assert all(lane['paired_committed'] for lane in projection['lanes'])
    assert all(lane['status'] == 'paired_committed' and not lane['halted'] for lane in projection['lanes'])
    assert projection['reference_request_mw'] == dict(numerator='0', denominator='1')
def ratio(value):
    return Q(int(value['numerator']), int(value['denominator']))
oracle = []
for lane_id in ('cfe', 'joint', 'network'):
    steps = [next(lane for lane in projection['lanes'] if lane['lane_id'] == lane_id) for projection in projections]
    actions = [step['business_candidate']['action'] for step in steps]
    assert steps[1]['before_actual'] == steps[0]['after_actual']
    assert steps[1]['before_business'] == steps[0]['after_business']
    q0 = ratio(actions[0]['grid_served'])+ratio(actions[0]['cfe_served'])
    r1 = ratio(actions[1]['recovery'])
    expected_r1 = Q((q0/Q(85, 100)*10**12).__floor__(), 10**12)
    assert r1 == expected_r1
    assert q0 == (Q(0) if lane_id == 'network' else Q(1, 50))
    assert ratio(actions[0]['recovery']) == 0
    assert ratio(actions[1]['grid_served'])+ratio(actions[1]['cfe_served']) == 0
    for action in actions:
        assert ratio(action['grid_served'])+ratio(action['cfe_served'])+ratio(action['recovery']) <= Q(1, 20)
    oracle.append(dict(lane=lane_id, hour0_call_normalized=str(q0), hour1_recovery_normalized=str(r1),
        hour1_debt_normalized=str(q0-Q(85, 100)*r1),
        actual_power_mw=[str(ratio(step['actual_power_mw'])) for step in steps]))
baseline_case = Path('D:/h1_cross_connected_04_non_authoritative/test_two_hour_three_lane_conne0')
old_rows = events(baseline_case/'owner_non_authoritative/owner.sqlite')
old_projection = next(row[2]['projection_sha256'] for row in old_rows if row[1] == 'outcome')
current_projection = next(row[2]['projection_sha256'] for row in rows if row[1] == 'outcome')
baseline_match = old_projection == current_projection
assert baseline_match
baseline05 = events(Path('D:/h1_cross_connected_05_non_authoritative/test_two_hour_three_lane_conne0/owner_non_authoritative/owner.sqlite'))
baseline05_projections = [row[2]['projection_sha256'] for row in baseline05 if row[1] == 'outcome']
current_projections = [row[2]['projection_sha256'] for row in rows if row[1] == 'outcome']
assert baseline05_projections == current_projections
timing_rows = [json.loads(line) for line in (case/'cross_hour_timing.jsonl').read_text(encoding='utf-8').splitlines()]
labels = [row['label'] for row in timing_rows]
assert labels == ['start', 'N0_terminal', 'hour0_paired', 'hour1_paired', 'closed_before_reopen', 'reopen_verified']
stage_seconds = {row['label']:row['monotonic']-previous['monotonic'] for previous,row in zip(timing_rows,timing_rows[1:])}
request = json.loads((attempt/'request.json').read_bytes())
assert request['seconds'] == 900 and request['mode'] == 'connected' and not request['native_calls_authorized']
for name, pin in request['sources_sha256'].items():
    assert sha256(Path(name).read_bytes()).hexdigest() == pin
added_static = {row['function']:row for row in bookends['functions']}
for name in ('experiments.h1_finite_followup_assessment_development_v1.implementation_identity',
             'experiments.h1_finite_followup_assessment_development_v1.contract_identity',
             'experiments.h1_phase_ticket_holder_development_v1.implementation_identity'):
    assert added_static[name]['calls'] > 0 and added_static[name]['bookends']
seconds = defaultdict(float)
counts = Counter()
for name, value in result['owner_stage_timings']:
    seconds[name] += value
    counts[name] += 1
postcheck = dict(status='DRAFT_NONAUTHORITATIVE', attempt=label, terminal=terminal,
    result_sha256=sha256(results[0].read_bytes()).hexdigest(), saved_file_count=result['saved_file_count'],
    all_saved_bytes_match=True, paired_lane_hours=6, oracle=oracle,
    phase_fresh_hours=dict(Counter(result['phase_fresh_hours'])),
    static_identity_calls=sum(row['calls'] for row in bookends['functions']),
    static_identity_original_computations=sum(row['original_computations'] for row in bookends['functions']),
    all_static_original_bookends_match=True, owner_stage_seconds=dict(seconds), owner_stage_counts=dict(counts),
    end_to_end_stage_seconds=stage_seconds, source_snapshots_match_current=True,
    read_only_predecessor_carry_links_match=True,
    baseline04_hour0_projection_sha256=old_projection, current_hour0_projection_sha256=current_projection,
    baseline04_hour0_scientific_projection_equal=baseline_match,
    baseline05_two_hour_scientific_projection_equal=True,
    baseline05_two_hour_projection_sha256=baseline05_projections,
    full_192_hour_execution_verified=False, formal_result=False, production_overhead_measured=False,
    complete_process_tree_absence_proven=False, persisted_atomic_live_join_authenticated=False)
output = HERE/(label+'_postcheck.json')
with output.open('x', encoding='utf-8') as stream:
    json.dump(postcheck, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(output=str(output), paired_lane_hours=6, oracle=oracle,
    baseline04_hour0_scientific_projection_equal=baseline_match,
    outer_seconds=terminal['outer_seconds'], owner_stage_seconds=dict(seconds),
    static_identity_calls=postcheck['static_identity_calls'],
    static_identity_original_computations=postcheck['static_identity_original_computations'])))
