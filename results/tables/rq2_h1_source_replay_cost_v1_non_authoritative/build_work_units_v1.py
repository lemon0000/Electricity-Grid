"""Extend the pinned workflow count model with observed Job/stage replay DAG."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def main():
    budget_path = REPO / 'results/tables/rq2_h1_phase_boundary_v1_non_authoritative/budget_audit_v1.json'
    budget = json.loads(budget_path.read_bytes())
    observed = json.loads((HERE / 'profile_02/reader_terminal.json').read_bytes())
    assert observed['exit_code'] == 0 and observed['call_counts'] == dict(inspect_job=12, timed_stage_inspect=60)
    functions = json.loads((HERE / 'profile_02/profile_functions.json').read_bytes())
    focused = [row for row in functions if
        (row['function'] in ('normal_input_identity', '_dependencies') and row['file'].endswith('continuous_grid_normal.py'))
        or row['function'] == 'version' and row['line'] == 882 and 'importlib' in row['file']]
    targets = {}
    for horizon in ('168', '192'):
        old = budget['target_work_units'][horizon]
        readers, weight = old['reader_observations'], old['reader_prefix_hour_weight']
        targets[horizon] = dict(condition='complete successful normal prefixes, fixed M stages per hour; no additional independent historical/snapshot probes',
            reader_observations=readers, reader_prefix_hour_weight=weight,
            current_parent_inspect_traversals=2 * readers,
            current_parent_prefix_hour_weight=2 * weight,
            current_bridge_inspect_calls=2 * weight,
            current_child_reference_inspect_calls=2 * weight,
            current_inspect_job_calls=4 * weight,
            current_stage_inspect_calls_formula='4*M*reader_prefix_hour_weight',
            current_toy_M5_stage_inspect_calls=20 * weight,
            conditional_constructor_reuse=dict(implemented=False, independently_validated=False,
                reader_observations=readers, parent_inspect_traversals=readers,
                parent_prefix_hour_weight=weight, inspect_job_calls=2 * weight,
                toy_M5_stage_inspect_calls=10 * weight),
            native_calls_implied_by_these_replay_counts=0,
            wall_prediction_seconds=None, total_wall_admission_seconds=None)
    sources = ('h1_cross_hour_owner_development_v2.py', 'h1_phase_exact_source_batch_development_v1.py',
        'h1_phase_historical_batch_development_v1.py', 'h1_historical_parent_prefix_development_v1.py',
        'h1_job_clock_bridge_development_v1.py', 'h1_timed_job_parent_development_v1.py',
        'h1_timed_worker_hour_development_v1.py', 'h1_timed_hour_development_v1.py',
        'h1_timed_stage_development_v1.py')
    bindings = {str(REPO / 'experiments' / name): sha256((REPO / 'experiments' / name).read_bytes()).hexdigest()
                for name in sources}
    for path in (budget_path, HERE / 'profile_02/reader_terminal.json', HERE / 'profile_02/profile_call_edges.json',
                 HERE / 'profile_02/profile_functions.json', Path(__file__)):
        bindings[str(path)] = sha256(path.read_bytes()).hexdigest()
    result = dict(status='DRAFT_NONAUTHORITATIVE', scope='source_layer_saved_scientific_replay_call_counts',
        dag=['prepare_many: two independent replay_prefixes around materialization',
             'each Reader: constructor self.inspect plus caller explicit inspect',
             'each traversal/hour: clock bridge inspect_job plus ChildReference inspect_job',
             'each inspect_job: one worker/hour replay and M timed stage inspections'],
        single_reader_formula=dict(parent_inspects=2, inspect_job='4*H', timed_stage_inspect='4*H*M'),
        observed_single_reader=dict(hours=3, M=5, inspect_job=12, timed_stage_inspect=60,
            source='profile_02', cprofile_overhead_included=True, fine_grained_focus=focused),
        target_work_units=targets, unknowns=['net whole-path effect of constructor reuse',
            'applicable runtime/freshness equivalence under removed traversal',
            'target-scale normal/source/history/serialization/failure/terminal wall RSS and storage'],
        existing_toy_event_cap_remains=32, minimum_events_at_192=576,
        optimization_implemented=False, overall_performance_review_complete=False,
        long_connected_launch_admitted=False, resource_admission=False, native_execution_authorized=False,
        formal_execution_ready=False, full_192_hour_execution_verified=False, real_native_calls=0,
        new_normal_jobs=0, formal_result=False, bindings=bindings)
    output = HERE / 'call_dag_and_work_units.json'
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(path=str(output), sha256=sha256(output.read_bytes()).hexdigest(), targets=targets)))


if __name__ == '__main__':
    main()
