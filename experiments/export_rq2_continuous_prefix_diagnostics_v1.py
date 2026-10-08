"""Small synthetic prefix delivery; no solver, formal runner, or checkpoint loader."""
from __future__ import annotations

import argparse
from dataclasses import fields, is_dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rq2_joint_deliverability_boundary_v1.boundary import BoundaryAnchor, ContinuationHour
from src.rq2_joint_deliverability_boundary_v1.causal_policy import (
    FixedPolicy, HourlyLimits, CurrentObservation, initialize_causal_policy,
    advance_causal_policy, summarize_policy_prefix,
)
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import NETWORK, CFE, JOINT, B6

CONFIG = 'configs/rq2_continuous_prefix_diagnostics_v1.DRAFT.yaml'
OUTPUT = ROOT/'results/tables/rq2_continuous_prefix_diagnostics_v1_non_authoritative'
ARMS = (NETWORK, CFE, JOINT, B6)
MODULES = ('__init__', 'boundary', 'multiday', 'debt_cohorts', 'four_arm_replay', 'causal_policy')
DEPENDENCIES = (CONFIG, 'experiments/export_rq2_continuous_prefix_diagnostics_v1.py',
    'tests/test_rq2_continuous_prefix_diagnostics_v1.py',
    'configs/rq2_continuous_causal_policy_v1.DRAFT.yaml',
    *(f'src/rq2_joint_deliverability_boundary_v1/{name}.py' for name in MODULES))
MEMBERS = ('config.json', 'inputs.jsonl', 'records.jsonl', 'summary.json', 'evidence.json', 'README.md')


def plain(value):
    """Exact rational values survive JSON; state snapshots exclude recursive plan history."""
    if isinstance(value, Fraction):
        return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}
    if is_dataclass(value):
        return {f.name: plain(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value


def encoded(value):
    return (json.dumps(plain(value), sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(',', ':'))+'\n').encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(cursor):
    if cursor is None:
        return None
    return plain({'arm_id': cursor.arm_id, 'mode': cursor.mode, 'tracks': dict(cursor.tracks)})


def make_inputs(config):
    if config['status'] != 'DRAFT_NONAUTHORITATIVE' or config['input_evidence'] != 'mechanism_assumption':
        raise ValueError('synthetic draft configuration required')
    if config['zero_carry_in_assumption'] is not True:
        raise ValueError('explicit synthetic zero history required')
    ids = [case['id'] for case in config['cases']]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError('nonempty unique cases required')
    rows = []
    for case in config['cases']:
        params = dict(config['defaults'], **{k: v for k, v in case.items() if k != 'id'})
        if type(params['hours']) is not int or not 1 <= params['hours'] <= 48:
            raise ValueError('tiny diagnostic horizon must be 1 to 48 hours')
        for t in range(1, params['hours']+1):
            active = t in params['call_hours']
            hour = dict(config['anchor'], power_source_hour=t,
                        workload_source_hour=config['anchor']['workload_source_hour']+t,
                        grid_request=params['grid_request'] if active else 0.,
                        cfe_request=params['cfe_request'] if active else 0.,
                        workload_occupancy=params['workload_occupancy'])
            limits = {key: params[key] for key in HourlyLimits.__dataclass_fields__}
            if t in params['recovery_blocked_hours']:
                limits['business_recovery_headroom'] = 0.
            due = t+params['deadline_offset_hours'] if active and params['deadline_offset_hours'] is not None else None
            obs = CurrentObservation(ContinuationHour(**hour), HourlyLimits(**limits), due)
            rows.append({'case_id': case['id'], 'evidence_class': 'mechanism_assumption',
                         'observation': plain(obs)})
    return rows


def replay(config, inputs):
    records, summaries = [], []
    for case in config['cases']:
        rows = [row for row in inputs if row['case_id'] == case['id']]
        for arm in ARMS:
            cursor = initialize_causal_policy(arm, policy=FixedPolicy(**config['policy']),
                anchor=BoundaryAnchor(**config['anchor']), envelope=config['envelope'],
                accounting_period_id=config['accounting_period_id'],
                zero_carry_in_assumption=config['zero_carry_in_assumption'])
            for row in rows:
                raw = row['observation']
                obs = CurrentObservation(ContinuationHour(**raw['hour']), HourlyLimits(**raw['limits']), raw['due_hour'])
                cursor = advance_causal_policy(cursor, obs)
                r = cursor.records[-1]
                records.append(plain({'case_id': case['id'], 'arm_id': arm,
                    'evidence_class': 'derived_synthetic_diagnostic', 'observation': obs,
                    'status': r.status, 'stage': r.stage, 'error': r.error,
                    'attempted_actions': dict(r.attempted_actions),
                    'attempted_actions_scope': 'separate_planning' if arm == B6 else 'physical_execution',
                    'accepted_physical_actions': dict(r.accepted_step.actions) if r.accepted_step else None,
                    'before_execution': snapshot(r.before_execution),
                    'before_planning': snapshot(r.before_planning),
                    'planned_candidate': snapshot(r.planned_step.cursor) if r.planned_step else None,
                    'committed_execution': snapshot(cursor.execution),
                    'committed_planning': snapshot(cursor.planning),
                    'prefix_summary': summarize_policy_prefix(cursor)}))
                if cursor.halted:
                    break
            summaries.append(plain(dict(summarize_policy_prefix(cursor), case_id=case['id'], arm_id=arm,
                configured_hours=len(rows), unsubmitted_hours=len(rows)-len(cursor.records),
                rejection_stage=cursor.records[-1].stage if cursor.halted else None,
                actual_rejected_hour_and_later_outcome=None)))
    return records, summaries


def build_payload():
    config = yaml.safe_load((ROOT/CONFIG).read_text(encoding='utf-8'))
    inputs = make_inputs(config)
    records, summaries = replay(config, inputs)
    evidence = {
        'real_observations_used': False,
        'input_values_policy_envelope_and_initial_state': 'mechanism_assumption',
        'anchor_ids_hashes_and_holdout_label': 'synthetic_identifiers_not_public_data_split',
        'known_deadlines': 'mechanism_assumption', 'null_deadlines': 'unidentified',
        'actions_states_and_summaries': 'derived_synthetic_diagnostic',
        'fraction_encoding': 'exact signed integer strings numerator/positive denominator',
        'snapshot_scope': 'physical_and_ledger_states; planning_history_reconstructed_by_full_replay',
        'failure_semantics': 'first_rejection_is_uncommitted; actual_failure_hour_and_suffix_unassessed',
        'full_horizon_risk_probability': None,
        'continuous_service_protocol_registered': False, 'formal_experiment_authorized': False,
        'formal_result': False, 'paper_claim': False, 'security_certified': False,
    }
    report = ['# 连续服务合成前缀诊断包', '', '状态：DRAFT_NONAUTHORITATIVE。全部输入为机制假设，未使用真实观测。',
        '四臂使用各场景相同的逐小时输入；已接受小时表示固定动作通过服务包络校验。',
        '首次拒绝小时及其后的实际服务结果未评价，不能从该包计算完整风险率或数学不可行性。', '',
        '| 场景 | 臂 | 配置小时 | 提交观测 | 接受小时 | 最后提交小时 | 拒绝阶段 | 逾期 cohort | unknown cohort | 截尾 cohort |',
        '|---|---|---:|---:|---:|---:|---|---:|---:|---:|']
    for row in summaries:
        report.append('| '+' | '.join(str(row[key]) for key in ('case_id', 'arm_id', 'configured_hours',
            'submitted_hours', 'accepted_hours', 'last_committed_power_hour', 'rejection_stage',
            'deadline_missed_count', 'deadline_unidentified_count', 'right_censored_count'))+' |')
    report += ['', 'config.json 保存解析后配置；inputs.jsonl 保存各场景完整合成输入序列。',
        'records.jsonl 只保存实际提交的前缀、当前观测、尝试动作、规划候选与提交状态。',
        'summary.json 按场景和臂分别计数，不跨场景合并为概率；精确债务见 numerator/denominator。',
        'diagnostic_manifest.json 是本地非权威文件清单，既不是 production manifest，也不构成运行授权。',
        '验证：python -B experiments/export_rq2_continuous_prefix_diagnostics_v1.py --verify-existing', '']
    return {'config.json': encoded(config), 'inputs.jsonl': b''.join(map(encoded, inputs)),
            'records.jsonl': b''.join(map(encoded, records)), 'summary.json': encoded(summaries),
            'evidence.json': encoded(evidence), 'README.md': '\n'.join(report).encode('utf-8')}


def manifest(payload):
    return {'schema': 'rq2_continuous_prefix_diagnostic_manifest_v1', 'status': 'DRAFT_NONAUTHORITATIVE',
            'formal_result': False, 'formal_experiment_authorized': False,
            'runtime': {'python': sys.version, 'pyyaml': yaml.__version__},
            'dependencies': {name: digest((ROOT/name).read_bytes()) for name in DEPENDENCIES},
            'files': {name: {'sha256': digest(data), 'bytes': len(data)} for name, data in payload.items()}}


def write_package(output=OUTPUT):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError('refusing to overwrite an existing diagnostic package')
    if not output.name.endswith('_non_authoritative'):
        raise ValueError('output must be explicitly non_authoritative')
    payload = build_payload()
    inventory = manifest(payload)
    output.mkdir(parents=True, exist_ok=False)
    for name, data in payload.items():
        with (output/name).open('xb') as stream:
            stream.write(data)
    with (output/'diagnostic_manifest.json').open('xb') as stream:
        stream.write(encoded(inventory))
    return verify_package(output)


def verify_package(output=OUTPUT):
    """Read-only exact-inventory, dependency, hash, and full deterministic replay check."""
    output = Path(output)
    expected_names = set(MEMBERS) | {'diagnostic_manifest.json'}
    if output.is_symlink() or {p.name for p in output.iterdir()} != expected_names:
        raise ValueError('diagnostic package inventory mismatch')
    if any(not (output/name).is_file() or (output/name).is_symlink() for name in expected_names):
        raise ValueError('regular package files required')
    inventory = json.loads((output/'diagnostic_manifest.json').read_bytes())
    actual = {name: (output/name).read_bytes() for name in MEMBERS}
    if inventory != manifest(actual):
        raise ValueError('diagnostic manifest or dependency/hash mismatch')
    expected = build_payload()
    if actual != expected:
        raise ValueError('deterministic replay mismatch')
    summaries = json.loads(actual['summary.json'])
    return {'status': 'DRAFT_NONAUTHORITATIVE', 'case_arm_count': len(summaries),
            'record_count': len(actual['records.jsonl'].splitlines()), 'replay_matches': True,
            'formal_result': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-existing', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify_package() if args.verify_existing else write_package(), sort_keys=True))
