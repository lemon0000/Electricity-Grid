"""Read-only inventory arithmetic from pinned local evidence; never runs a solver."""
import ast
from datetime import datetime, timedelta
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import yaml
from src.rq2_joint_deliverability_boundary_v1 import execution_workload as workload

PINS = {
    'results/tables/rq2_source_pairs_v1_non_authoritative/normal_dynamic_verified_non_authoritative.json':
        '8c9b58ff3de2f37fecddcc283a1950e91c917a0dd0fc3d4c9025c29af317707d',
    'configs/rq2_normal_task_gurobi_ordered_h25_development_v1.DRAFT.yaml':
        '688c2090f8e26c08b744fea7f61dfef38726d29ed69163727efa23575ccca03d',
    'configs/rq2_joint_deliverability_preregistration_v1.yaml':
        '2efd3fa275cccde2aee701662bb2718386b2fb54d2846b090d0828d8409bdc4f',
    'data/processed/rq2_public_data_delivery_v1_non_authoritative/input_status.json':
        '263643c83cf4ec60fd25fb176f50c3aae2bd7f158f8bb550fe241f3a18d88302',
}


def audit():
    evidence = {}
    for name, pin in PINS.items():
        raw = (ROOT/name).read_bytes()
        if sha256(raw).hexdigest() != pin:
            raise ValueError('pinned evidence changed: '+name)
        evidence[name] = json.loads(raw) if name.endswith('.json') else yaml.safe_load(raw)
    record, old, science, status = (evidence[name] for name in PINS)
    uids = tuple(sorted(record['initial']['commitment']))
    if any(tuple(sorted(values)) != uids for values in (
            record['initial']['generation_mw'], record['request']['initial_commitment'])):
        raise ValueError('source UID inventories differ')
    hours = tuple(record['binding']['power_source_hours'])
    stamps = tuple(datetime.fromisoformat(x) for x in record['request']['timestamps'])
    if (len(hours) != len(stamps) or any(b-a != timedelta(hours=1) for a,b in zip(stamps,stamps[1:]))):
        raise ValueError('source clock is not contiguous')
    input_pin = record['normal_input_identity']
    if input_pin != old['request']['source']['expected_input_identity']:
        raise ValueError('old task does not reference this source input')
    normal_seconds = old['request']['specification']['time_limit_seconds']
    if normal_seconds != int(normal_seconds):
        raise ValueError('integer diagnostic reservation required')
    normal = workload.NormalWork('existing_h25_normal', 'training', input_pin, uids, hours, int(normal_seconds))
    process_path = ROOT/'src/rq2_joint_deliverability_boundary_v1/normal_task_process.py'
    tree = ast.parse(process_path.read_text(encoding='utf-8'))
    caps = [n.comparators[0].value for n in ast.walk(tree)
        if isinstance(n, ast.Compare) and isinstance(n.left, ast.Attribute)
        and n.left.attr == 'max_elapsed_seconds' and len(n.ops) == 1 and isinstance(n.ops[0], ast.Gt)
        and isinstance(n.comparators[0], ast.Constant)]
    if caps != [3600]:
        raise ValueError('review required for changed process ceiling')
    n, h, cap = len(uids), len(hours), caps[0]
    rows = []
    for seconds in (1, 5, 15, 22, 23, 30):
        episode = workload.EpisodeWork('arithmetic_h25_episode', 'training', normal.task_id,
            input_pin, uids, hours, seconds, (seconds,)*4)
        report = workload.summarize_workload((normal,), (episode,))
        reference, actual = (n+2)*seconds, (n+1)*seconds
        expected_calls = 1 + h*((n+2)+4*(n+1))
        expected_seconds = normal.seconds_per_solve + (expected_calls-1)*seconds
        if (report['solver_calls'], report['reserved_solver_seconds']) != (expected_calls, expected_seconds):
            raise ValueError('independent arithmetic differs from workload utility')
        rows.append(dict(selector_seconds_per_solve=seconds, normal_seconds_per_solve=normal.seconds_per_solve,
            solver_calls=expected_calls, reserved_solver_seconds=expected_seconds,
            reserved_solver_hours=str(Fraction(expected_seconds,3600)),
            reference_phase_solver_seconds=reference, actual_phase_solver_seconds=actual,
            reference_non_solver_room_before_process_ceiling=cap-reference,
            actual_non_solver_room_before_process_ceiling=cap-actual,
            solver_reservation_alone_exceeds_phase_ceiling=max(reference,actual)>cap,
            runtime_admission_proven=False))
    design = science['registered_design']
    factorial = 1
    for values in design['primary_factorial']['factors'].values(): factorial *= len(values)
    oat = sum(sum(v != design['secondary_oat']['anchor'][name] for v in values)
        for name,values in design['secondary_oat']['varied_levels'].items())
    if (factorial, oat, factorial+oat) != (36,10,design['exact_unique_cell_count']):
        raise ValueError('old registered cell arithmetic differs')
    if any(x['value'] is not None for x in status['unidentified']):
        raise ValueError('empirical evidence changed; reassess registration gaps')
    return dict(schema='rq2_current_workload_inventory_audit_v1', scope='existing_h25_and_conditional_arithmetic',
        evidence_sha256=PINS, implementation_sha256={str(p.relative_to(ROOT)).replace('\\','/'):sha256(p.read_bytes()).hexdigest()
            for p in (Path(__file__).resolve(), Path(workload.__file__).resolve(), process_path)},
        existing_source=dict(normal_input_identity=input_pin, generator_uids=uids, source_hours=hours,
            first_timestamp=stamps[0].isoformat(),last_timestamp=stamps[-1].isoformat(),
            generator_count=n,hours=h,normal_model_scale=record['model_scale'],
            parameter_role='mechanism_assumption',registered_coupling=False,observed_power_mapping=False),
        old_registered_cells=dict(factorial=factorial,oat_added=oat,total=factorial+oat,
            continuous_successor_registered=False,cell_count_is_not_episode_count=True),
        phase_process_ceiling_seconds=cap,conditional_budget_rows=rows,
        unidentified_inputs=[x['name'] for x in status['unidentified']],
        unregistered_choices=[k for k,v in status['protocol_choices'].items() if v['status']=='unregistered'],
        missing_full_inventory=['continuous_cells_and_windows','couplings_and_weights',
            'training_capacity_evaluations','holdout_capacity_and_policy_bindings',
            'normal_reuse_and_information_declarations','pilot_and_retry_tasks',
            'phase_wall_memory_archive_scratch_allocations','replay_and_parent_audit_allocations'],
        full_experiment_solver_calls=None,full_experiment_wall_seconds=None,
        solver_calls_by_audit=0,budget_recommendation=False,formal_ready=False,execution_authorized=False)


if __name__ == '__main__':
    print(json.dumps(audit(),ensure_ascii=True,sort_keys=True,indent=2,allow_nan=False))
