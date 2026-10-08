"""Non-authoritative composite-policy delivery, fixed tiny scenarios only."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from experiments import export_rq2_continuous_prefix_diagnostics_v1 as prefix
from src.rq2_joint_deliverability_boundary_v1.boundary import BoundaryAnchor,ContinuationHour
from src.rq2_joint_deliverability_boundary_v1.causal_policy import CurrentObservation,HourlyLimits
from src.rq2_joint_deliverability_boundary_v1.recovery_controller import (
    CompositePolicy,initialize_composite_policy,advance_composite_policy,summarize_composite_policy,
)

CONFIG = 'configs/rq2_continuous_composite_diagnostics_v1.DRAFT.yaml'
SCENARIOS = prefix.CONFIG
CONTROLLER = 'configs/rq2_continuous_recovery_controller_v1.DRAFT.yaml'
OUTPUT = ROOT/'results/tables/rq2_continuous_composite_diagnostics_v1_non_authoritative'
MEMBERS = ('config.json','inputs.jsonl','policies.json','records.jsonl','summary.json','evidence.json','README.md')
DEPENDENCIES = tuple(dict.fromkeys((*prefix.DEPENDENCIES,CONFIG,CONTROLLER,
    'experiments/export_rq2_continuous_composite_diagnostics_v1.py',
    'tests/test_rq2_continuous_composite_diagnostics_v1.py',
    'src/rq2_joint_deliverability_boundary_v1/actual_actions.py',
    'src/rq2_joint_deliverability_boundary_v1/recovery_controller.py')))


def load_inputs():
    config=yaml.safe_load((ROOT/CONFIG).read_text(encoding='utf-8'))
    expected={'schema':'rq2_continuous_composite_diagnostics_v1','status':'DRAFT_NONAUTHORITATIVE',
        'evidence_class':'mechanism_assumption','scenario_config':SCENARIOS,'controller_config':CONTROLLER}
    if set(config)!=set(expected)|{'extra_cases'} or any(config[k]!=v for k,v in expected.items()):
        raise ValueError('fixed synthetic delivery configuration required')
    if not isinstance(config['extra_cases'],list) or len(config['extra_cases'])>2:
        raise ValueError('at most two tiny supplemental cases allowed')
    scenarios=yaml.safe_load((ROOT/SCENARIOS).read_text(encoding='utf-8'))
    controller=yaml.safe_load((ROOT/CONTROLLER).read_text(encoding='utf-8'))
    expanded=deepcopy(scenarios)
    for case in config['extra_cases']:
        if set(case)!={'id','cfe_request','input_role','overrides'}:
            raise ValueError('unsupported extra scenario fields')
        if case['input_role'] not in {'synthetic_mechanism','synthetic_identity_fault_injection'}:
            raise ValueError('explicit synthetic input role required')
        if (any('power_source_hour' in changes for changes in case['overrides'].values())
            and case['input_role']!='synthetic_identity_fault_injection'):
            raise ValueError('source-hour fault must be labelled fault injection')
        expanded['cases'].append({k:case[k] for k in ('id','cfe_request')})
    rows=prefix.make_inputs(expanded)
    extras={case['id']:case for case in config['extra_cases']}
    for row in rows:
        case=extras.get(row['case_id'])
        row['input_role']=case['input_role'] if case else 'synthetic_mechanism'
        if case:
            for hour,changes in case['overrides'].items():
                if type(hour) is not int or hour<1 or hour>expanded['defaults']['hours']:
                    raise ValueError('override hour outside configured window')
                if set(changes)-{'power_source_hour','grid_request','cfe_request'}:
                    raise ValueError('unsupported diagnostic override')
            current=row['observation']['hour']['power_source_hour']
            row['observation']['hour'].update(case['overrides'].get(current,{}))
        raw=row['observation']
        CurrentObservation(ContinuationHour(**raw['hour']),HourlyLimits(**raw['limits']),raw['due_hour'])
    return {'delivery':config,'scenarios':expanded,'controller':controller},rows


def execution(cursor):
    return cursor.actual.execution if cursor.actual is not None else cursor.primary.execution


def composite_summary(cursor):
    summary=summarize_composite_policy(cursor)
    summary['original_rejection_raw_source_hour']=summary.pop('original_rejection_hour')
    summary['original_rejection_submission_index']=len(cursor.primary.records) if cursor.primary.halted else None
    return summary


def primary_event(record):
    return prefix.plain({'status':record.status,'stage':record.stage,'error':record.error,
        'attempted_actions':dict(record.attempted_actions),
        'before_planning':prefix.snapshot(record.before_planning),
        'planned_candidate':prefix.snapshot(record.planned_step.cursor) if record.planned_step else None,
        'accepted_actions':dict(record.accepted_step.actions) if record.accepted_step else None})


def replay(config,inputs):
    records,summaries,policies=[],[],{}
    scenarios=config['scenarios']
    for case in scenarios['cases']:
        rows=[r for r in inputs if r['case_id']==case['id']]
        for arm in prefix.ARMS:
            spec=CompositePolicy.from_config(config['controller'],arm)
            policies[spec.policy_id]=prefix.plain(spec)
            cursor=initialize_composite_policy(spec,anchor=BoundaryAnchor(**scenarios['anchor']),
                envelope=scenarios['envelope'],accounting_period_id=scenarios['accounting_period_id'],
                zero_carry_in_assumption=scenarios['zero_carry_in_assumption'])
            for index,row in enumerate(rows,1):
                before=cursor
                raw=row['observation']
                observation=CurrentObservation(ContinuationHour(**raw['hour']),HourlyLimits(**raw['limits']),raw['due_hour'])
                cursor=advance_composite_policy(cursor,observation)
                primary=None
                if len(cursor.primary.records)>len(before.primary.records):
                    primary=primary_event(cursor.primary.records[-1])
                recovery=None
                if len(cursor.recovery_records)>len(before.recovery_records):
                    decision=cursor.recovery_records[-1]
                    actual=decision.after.records[-1] if decision.after is not None else None
                    recovery=prefix.plain({'stage':decision.stage,'error':decision.error,
                        'action':actual.action if actual else None,
                        'actual_status':actual.status if actual else None})
                outcome='unassessed' if cursor.stopped else ('recovery_validated' if recovery else 'primary_validated')
                records.append(prefix.plain({'case_id':case['id'],'arm_id':arm,'policy_id':cursor.policy_id,
                    'submission_index':index,'input_role':row['input_role'],'evidence_class':'derived_synthetic_diagnostic',
                    'observation':observation,'outcome':outcome,'primary_event':primary,'recovery_event':recovery,
                    'before_execution':prefix.snapshot(execution(before)),
                    'committed_execution':prefix.snapshot(execution(cursor)),
                    'primary_planning_archive':prefix.snapshot(cursor.primary.planning),
                    'prefix_summary':composite_summary(cursor)}))
                if cursor.stopped:
                    break
            summary=composite_summary(cursor)
            summary.update(case_id=case['id'],arm_id=arm,configured_input_count=len(rows),
                unsubmitted_input_count=len(rows)-summary['submitted_unique_hours'],
                first_unassessed_submission_index=index if cursor.stopped else None,
                first_unassessed_source_hour=observation.hour.power_source_hour if cursor.stopped else None,
                unassessed_stage=(recovery['stage'] if recovery else primary['stage']) if cursor.stopped else None,
                unassessed_error=(recovery['error'] if recovery else primary['error']) if cursor.stopped else None,
                actual_unassessed_hour_and_suffix_outcome=None)
            summaries.append(prefix.plain(summary))
    return records,summaries,policies


def build_payload():
    config,inputs=load_inputs()
    records,summaries,policies=replay(config,inputs)
    evidence={'real_observations_used':False,'inputs_parameters_and_policy':'mechanism_assumption',
        'actions_states_summaries':'derived_synthetic_diagnostic',
        'null_deadline':'unidentified','known_deadline':'mechanism_assumption',
        'identifiers_and_holdout_label':'synthetic_not_empirical_split',
        'policy_id_scope':'composite_rule_not_original_B6_or_experiment_identity',
        'counting':'one_record_per_submitted_input; primary_rejection_and_recovery_share_one_record',
        'invalid_source_hour':'raw_identifier_not_validated_exposure',
        'fraction_encoding':'exact_integer_strings_numerator_denominator',
        'continuous_service_protocol_registered':False,'formal_experiment_authorized':False,
        'formal_result':False,'paper_claim':False,'security_certified':False,'risk_probability':None}
    report=['# 组合策略后继诊断包','','DRAFT_NONAUTHORITATIVE；输入和策略均为合成机制假设。',
        '原策略拒绝与同小时补救分别保存，小时计数不重复。B6组合策略拥有独立policy_id，不能写回旧B6结果。',
        '未评价小时保持最后已验证状态；收到错误来源标识不等于验证了该小时。计数不用于经验风险概率。','',
        '| 场景 | 臂 | 输入提交数 | 原策略接受 | 补救验证 | 总验证 | 未提交输入 | 首个未评价输入序号 | 停止阶段 |',
        '|---|---|---:|---:|---:|---:|---:|---:|---|']
    for row in summaries:
        report.append('| '+' | '.join(str(row[k]) for k in ('case_id','arm_id','submitted_unique_hours',
            'primary_accepted_hours','recovery_validated_hours','validated_unique_hours','unsubmitted_input_count',
            'first_unassessed_submission_index','unassessed_stage'))+' |')
    report+=['','inputs.jsonl保存完整场景输入；records.jsonl只保存提交前缀及原策略/补救子记录。',
        'policy_id与策略参数见policies.json；配置、精确cohort余额和原始错误保存在对应JSON成员。',
        'diagnostic_manifest.json仅是本地非权威清单；验证依赖相同本地代码和Python/PyYAML版本。',
        '验证：python -B experiments/export_rq2_continuous_composite_diagnostics_v1.py --verify-existing','']
    return {'config.json':prefix.encoded(config),'inputs.jsonl':b''.join(map(prefix.encoded,inputs)),
        'policies.json':prefix.encoded(policies),'records.jsonl':b''.join(map(prefix.encoded,records)),
        'summary.json':prefix.encoded(summaries),'evidence.json':prefix.encoded(evidence),
        'README.md':'\n'.join(report).encode('utf-8')}


def manifest(payload):
    return {'schema':'rq2_continuous_composite_diagnostic_manifest_v1','status':'DRAFT_NONAUTHORITATIVE',
        'formal_result':False,'formal_experiment_authorized':False,
        'runtime':{'python':sys.version,'pyyaml':yaml.__version__},
        'dependencies':{name:prefix.digest((ROOT/name).read_bytes()) for name in DEPENDENCIES},
        'files':{name:{'sha256':prefix.digest(data),'bytes':len(data)} for name,data in payload.items()}}


def write_package(output=OUTPUT):
    output=Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError('refusing to overwrite existing composite package')
    if not output.name.endswith('_non_authoritative'):
        raise ValueError('explicit non_authoritative output required')
    payload=build_payload()
    inventory=manifest(payload)
    output.mkdir(parents=True,exist_ok=False)
    for name,data in payload.items():
        with (output/name).open('xb') as stream:
            stream.write(data)
    with (output/'diagnostic_manifest.json').open('xb') as stream:
        stream.write(prefix.encoded(inventory))
    return verify_package(output)


def verify_package(output=OUTPUT):
    output=Path(output)
    names=set(MEMBERS)|{'diagnostic_manifest.json'}
    if output.is_symlink() or {p.name for p in output.iterdir()}!=names:
        raise ValueError('composite inventory mismatch')
    if any(not (output/n).is_file() or (output/n).is_symlink() for n in names):
        raise ValueError('regular files required')
    payload={name:(output/name).read_bytes() for name in MEMBERS}
    if json.loads((output/'diagnostic_manifest.json').read_bytes())!=manifest(payload):
        raise ValueError('composite manifest/dependency/hash mismatch')
    if payload!=build_payload():
        raise ValueError('composite deterministic replay mismatch')
    return {'status':'DRAFT_NONAUTHORITATIVE','case_arm_count':len(json.loads(payload['summary.json'])),
        'record_count':len(payload['records.jsonl'].splitlines()),'replay_matches':True,'formal_result':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-existing',action='store_true')
    args=parser.parse_args()
    print(json.dumps(verify_package() if args.verify_existing else write_package(),sort_keys=True))
