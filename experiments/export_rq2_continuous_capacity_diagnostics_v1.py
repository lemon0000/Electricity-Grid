"""Exact fixed-capacity policy diagnostics on tiny synthetic continuous inputs."""
import argparse
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as Q
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import export_rq2_continuous_prefix_diagnostics_v1 as prefix
from src.rq2_joint_deliverability_boundary_v1.boundary import BoundaryAnchor, ContinuationHour
from src.rq2_joint_deliverability_boundary_v1.causal_policy import CurrentObservation, HourlyLimits
from src.rq2_joint_deliverability_boundary_v1.capacity_policy import (
    CapacityPolicy, CapacityObservation, initialize_capacity_policy, advance_capacity_policy,
)
from src.rq2_joint_deliverability_boundary_v1.debt_cohorts import assess_debt_cohorts

CONFIG = 'configs/rq2_continuous_capacity_policy_v1.DRAFT.yaml'
OUTPUT = ROOT/'results/tables/rq2_continuous_capacity_diagnostics_v1_non_authoritative'
MEMBERS = ('config.json', 'inputs.jsonl', 'policies.json', 'records.jsonl', 'summary.json', 'evidence.json', 'README.md')
DEPENDENCIES = tuple(dict.fromkeys((*prefix.DEPENDENCIES, CONFIG,
    'experiments/__init__.py', 'src/__init__.py',
    'experiments/export_rq2_continuous_capacity_diagnostics_v1.py',
    'tests/test_rq2_continuous_capacity_diagnostics_v1.py',
    'tests/test_rq2_continuous_capacity_policy_v1.py',
    'tests/test_rq2_continuous_recovery_controller_v1.py',
    'configs/rq2_continuous_recovery_controller_v1.DRAFT.yaml',
    *(f'src/rq2_joint_deliverability_boundary_v1/{name}.py'
      for name in ('actual_actions', 'aggregate_response', 'capacity_policy', 'recovery_controller')))))


def load_inputs():
    scenarios = yaml.safe_load((ROOT/prefix.CONFIG).read_text(encoding='utf-8'))
    scenarios = deepcopy(scenarios)
    # These are explicitly synthetic diagnostics, not training or protocol choices.
    scenarios['cases'] += [
        {'id': 'capacity_grid_stop', 'hours': 4, 'call_hours': [1], 'grid_request': .25},
        {'id': 'capacity_cfe_partial', 'hours': 4, 'call_hours': [1, 2],
         'grid_request': .125, 'cfe_request': .25},
        {'id': 'capacity_source_gap', 'hours': 4, 'call_hours': [1], 'grid_request': .125},
    ]
    policy = yaml.safe_load((ROOT/CONFIG).read_text(encoding='utf-8'))
    for arm in prefix.ARMS:
        CapacityPolicy.from_config(policy, arm)
    rows = prefix.make_inputs(scenarios)
    for row in rows:
        row['available_flexibility'] = policy['fixture']['available_flexibility']
        row['input_role'] = 'synthetic_mechanism'
        if row['case_id'] == 'capacity_source_gap':
            row['input_role'] = 'synthetic_identity_fault_injection'
            if row['observation']['hour']['power_source_hour'] == 2:
                row['observation']['hour']['power_source_hour'] = 99
    return {'scenarios': scenarios, 'policy': policy}, rows


def summarize(cursor, configured_input_count):
    if type(configured_input_count) is not int or configured_input_count < len(cursor.records):
        raise ValueError('configured count must cover the submitted prefix')
    responses = [r.response for r in cursor.records if r.response is not None
                 and r.response.candidate_step is not None]
    committed = [r for r in responses if r.committed]
    dt = Q(str(dict(cursor.initial.tracks[0][1].physical.envelope)['time_step_hours']))

    def energy(items, field):
        values = [getattr(r, field) for r in items]
        applicable = cursor.spec.arm_id != (prefix.CFE if field == 'grid_shortfall' else prefix.NETWORK)
        return sum((v*dt for v in values if v is not None), Q(0)) if applicable else None

    stopped = cursor.records[-1] if cursor.stopped else None
    return {
        'policy_id': cursor.policy_id, 'arm_id': cursor.spec.arm_id,
        'evidence_class': 'derived_synthetic_diagnostic',
        'configured_input_count': configured_input_count,
        'submitted_input_count': len(cursor.records), 'committed_input_count': len(committed),
        'evaluated_candidate_count': len(responses),
        'unassessed_submitted_count': len(cursor.records)-len(responses),
        'unsubmitted_input_count': configured_input_count-len(cursor.records),
        'evaluated_candidate_grid_shortfall_energy': energy(responses, 'grid_shortfall'),
        'evaluated_candidate_cfe_shortfall_energy': energy(responses, 'cfe_shortfall'),
        'committed_grid_shortfall_energy': energy(committed, 'grid_shortfall'),
        'committed_cfe_shortfall_energy': energy(committed, 'cfe_shortfall'),
        'evaluated_candidate_grid_failure_count': sum(r.grid_service_failure is True for r in responses),
        'evaluated_candidate_cfe_failure_count': sum(r.cfe_service_failure is True for r in responses),
        'stopped': cursor.stopped,
        'stop_submission_index': len(cursor.records) if stopped else None,
        'stop_raw_source_hour': stopped.current.observation.hour.power_source_hour if stopped else None,
        'stop_stage': stopped.stage if stopped else None,
        'stop_error': stopped.error if stopped else None,
        'last_committed_source_hour': cursor.execution.tracks[0][1].physical.anchor.power_source_hour,
        'remaining_debt': tuple((name, track.ledger.debt) for name, track in cursor.execution.tracks),
        'cohort_statuses': tuple((name, birth, status) for name, track in cursor.execution.tracks
                                 for birth, status in assess_debt_cohorts(track.ledger)),
        'uncommitted_hour_and_suffix_actual_outcome': None,
        'full_service_outcome': None, 'risk_probability': None,
        'completion_claim_allowed': False, 'formal_result': False,
    }


def replay(config, inputs):
    records, summaries, policies = [], [], {}
    scenarios = config['scenarios']
    for case in scenarios['cases']:
        rows = [r for r in inputs if r['case_id'] == case['id']]
        for arm in prefix.ARMS:
            spec = CapacityPolicy.from_config(config['policy'], arm)
            cursor = initialize_capacity_policy(spec, anchor=BoundaryAnchor(**scenarios['anchor']),
                envelope=scenarios['envelope'], accounting_period_id=scenarios['accounting_period_id'],
                zero_carry_in_assumption=scenarios['zero_carry_in_assumption'])
            policies[cursor.policy_id] = prefix.plain({'spec': spec, 'initial': prefix.snapshot(cursor.initial)})
            for index, row in enumerate(rows, 1):
                raw = row['observation']
                observation = CurrentObservation(ContinuationHour(**raw['hour']), HourlyLimits(**raw['limits']), raw['due_hour'])
                current = CapacityObservation(observation, row['available_flexibility'])
                before = cursor.execution
                cursor = advance_capacity_policy(cursor, current)
                record = cursor.records[-1]
                response = record.response
                projection = None
                if response is not None:
                    action = response.action
                    projection = replace(observation, hour=replace(observation.hour,
                        grid_request=action.grid_served, cfe_request=action.cfe_served),
                        due_hour=observation.due_hour if action.grid_served+action.cfe_served else None)
                records.append(prefix.plain({
                    'case_id': case['id'], 'arm_id': arm, 'policy_id': cursor.policy_id,
                    'submission_index': index, 'input_role': row['input_role'],
                    'evidence_class': 'derived_synthetic_diagnostic',
                    'original_current': current, 'executed_request_projection': projection,
                    'stage': record.stage, 'error': record.error,
                    'response_status': response.status if response else None,
                    'declared_action': response.action if response else None,
                    'grid_shortfall': response.grid_shortfall if response else None,
                    'cfe_shortfall': response.cfe_shortfall if response else None,
                    'candidate_business_validated': response is not None and response.candidate_step is not None,
                    'committed': record.committed,
                    'before_execution': prefix.snapshot(before),
                    'candidate_execution': prefix.snapshot(response.candidate_step.cursor)
                        if response is not None and response.candidate_step is not None else None,
                    'committed_execution': prefix.snapshot(cursor.execution),
                }))
                if cursor.stopped:
                    break
            summaries.append(prefix.plain(dict(summarize(cursor, len(rows)), case_id=case['id'])))
    return records, summaries, policies


def build_payload():
    config, inputs = load_inputs()
    records, summaries, policies = replay(config, inputs)
    evidence = {
        'real_observations_used': False, 'inputs_parameters_and_policy': 'mechanism_assumption',
        'actions_states_summaries': 'derived_synthetic_diagnostic',
        'training_capacity_certificate': None, 'risk_probability': None,
        'fraction_encoding': 'exact_integer_strings_numerator_denominator',
        'energy_scope': 'normalized_power_times_hours; evaluated_candidates_and_committed_prefix_separate',
        'tiny_shortfalls': 'accumulated_exactly_even_when_hourly_failure_flag_is_false',
        'cohort_scope': 'committed_state_only; unknown_deadlines_and_right_censoring_preserved',
        'candidate_scope': 'mechanism_candidate_not_observed_actual_execution',
        'source_gap': 'raw_source_identifier_not_validated_exposure',
        'split_and_source_identifiers': 'synthetic_not_empirical_split_or_provenance',
        'continuous_service_protocol_registered': False, 'formal_experiment_authorized': False,
        'formal_result': False, 'paper_claim': False, 'security_certified': False,
    }
    report = ('# 固定容量连续策略诊断包\n\nDRAFT_NONAUTHORITATIVE；输入、容量和响应参数为合成机制假设。\n'
        '原始请求、精确执行投影、业务候选与已提交状态分别保存；未提交候选不是实际履约。\n'
        '短缺能量按归一化功率×小时精确累加，包括逐小时容差内短缺；不产生经验风险概率。\n'
        'cohort仅取已提交状态，保留未知期限、逾期和右删失；完整服务结论保持null。\n'
        '本地清单校验成员、依赖及确定性重放，不是正式manifest或防篡改签名。\n\n'
        '验证：python -B experiments/export_rq2_continuous_capacity_diagnostics_v1.py --verify-existing\n')
    return {'config.json': prefix.encoded(config), 'inputs.jsonl': b''.join(map(prefix.encoded, inputs)),
        'policies.json': prefix.encoded(policies), 'records.jsonl': b''.join(map(prefix.encoded, records)),
        'summary.json': prefix.encoded(summaries), 'evidence.json': prefix.encoded(evidence),
        'README.md': report.encode('utf-8')}


def manifest(payload):
    return {'schema': 'rq2_continuous_capacity_diagnostic_manifest_v1', 'status': 'DRAFT_NONAUTHORITATIVE',
        'formal_result': False, 'formal_experiment_authorized': False,
        'runtime': {'python': sys.version, 'pyyaml': yaml.__version__},
        'dependencies': {name: prefix.digest((ROOT/name).read_bytes()) for name in DEPENDENCIES},
        'files': {name: {'sha256': prefix.digest(data), 'bytes': len(data)} for name, data in payload.items()}}


def write_package(output=OUTPUT):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError('refusing to overwrite existing capacity package')
    if not output.name.endswith('_non_authoritative'):
        raise ValueError('explicit non_authoritative output required')
    payload = build_payload()
    inventory = manifest(payload)
    output.mkdir(parents=True, exist_ok=False)
    for name, data in dict(payload, **{'diagnostic_manifest.json': prefix.encoded(inventory)}).items():
        with (output/name).open('xb') as stream:
            stream.write(data)
    return verify_package(output)


def verify_package(output=OUTPUT):
    output = Path(output)
    names = set(MEMBERS)|{'diagnostic_manifest.json'}
    if output.is_symlink() or {p.name for p in output.iterdir()} != names:
        raise ValueError('capacity inventory mismatch')
    if any(not (output/n).is_file() or (output/n).is_symlink() for n in names):
        raise ValueError('regular files required')
    payload = {name: (output/name).read_bytes() for name in MEMBERS}
    if json.loads((output/'diagnostic_manifest.json').read_bytes()) != manifest(payload):
        raise ValueError('capacity manifest/dependency/hash mismatch')
    if payload != build_payload():
        raise ValueError('capacity deterministic replay mismatch')
    return {'status': 'DRAFT_NONAUTHORITATIVE', 'case_arm_count': len(json.loads(payload['summary.json'])),
        'record_count': len(payload['records.jsonl'].splitlines()), 'replay_matches': True, 'formal_result': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-existing', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify_package() if args.verify_existing else write_package(), sort_keys=True))
