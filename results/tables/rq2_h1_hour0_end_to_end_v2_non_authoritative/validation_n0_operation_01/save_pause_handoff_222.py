"""Save a paused status snapshot and synchronize handoff pointers; no experiment."""
from datetime import datetime,timedelta,timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import psutil

H=Path(__file__).resolve().parent;R=H.parents[3]
D=H/'whole_workflow_optimization_01_non_authoritative'
now=datetime.now(timezone.utc);stamp=now.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S +08')
def pin(path):
    path=Path(path)
    return dict(path=str(path.relative_to(R)) if path.is_relative_to(R) else str(path),
        sha256=sha256(path.read_bytes()).hexdigest())
def project_path(value):
    path=Path(value);return path if path.is_absolute() else R/path
def write_json(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')

latest=json.loads((D/'source_factory_evidence_221.json').read_bytes())
assert latest['terminal']['exit_code']==0 and latest['terminal']['source_unchanged']
for row in latest['archive_files']:
    assert sha256(project_path(row['saved']).read_bytes()).hexdigest()==row['sha256']
current=[]
archive=D/'source_factory_221_preserved_non_authoritative'
for stem in ('h1_validation_callable_state_development_v1','h1_common_registry_factory_development_v1'):
    for relative in ('experiments/'+stem+'.py','tests/test_'+stem+'.py'):
        path=R/relative;row=pin(path)
        row['matches_221_saved_bytes']=path.read_bytes()==(archive/path.name).read_bytes()
        current.append(row)
assert all(row['matches_221_saved_bytes'] for row in current)

core=json.loads((D/'roster_scoped_findings_202.json').read_bytes())
core_pins=[dict(source=row['source'],matches_202=sha256(project_path(row['source']).read_bytes()).hexdigest()==row['sha256'])
    for row in core['source_snapshots']]
graph=json.loads((D/'common_typed_graph_evidence_207.json').read_bytes())
graph_pins=[dict(source=row['path'],matches_207=sha256(project_path(row['path']).read_bytes()).hexdigest()==row['sha256'])
    for row in graph['sources']]
legacy_path=H.parent/'chain_07/postcheck_supplement_completion_04.json'
legacy=json.loads(legacy_path.read_bytes())
legacy_pins=[dict(path=path,matches_saved_receipt=sha256(Path(path).read_bytes()).hexdigest()==expected)
    for path,expected in legacy['files_sha256'].items()]
assert all(row['matches_saved_receipt'] for row in legacy_pins)
processes=[]
for process in psutil.process_iter(['pid','name','create_time','ppid']):
    try:
        name=(process.info['name'] or '').lower()
        if process.pid!=os.getpid() and any(part in name for part in ('python','pytest','gurobi','cplex','ipopt')):
            processes.append(process.info)
    except (psutil.NoSuchProcess,psutil.AccessDenied):pass

handoff=H/'continuation_handoff_20261019_pause.md'
value=dict(schema='h1_paused_handoff_state_222',at_utc=now.isoformat(),goal_status='paused',
    objective='先把实验未完成的部分给做完，接着把实验过程要优化的瓶颈完成',
    goal_complete=False,handoff=pin(handoff),observed_related_processes=processes,
    process_observation_scope='one current name/PID/creation-time snapshot; current writer excluded',
    complete_process_tree_absence_proven=False,
    legacy_body_and_postcheck_complete=True,legacy_postcheck=pin(legacy_path),legacy_receipt_current_pins=legacy_pins,
    core_202_named_source_pins=core_pins,typed_graph_207_source_pins=graph_pins,
    current_helper_sources=current,latest_helper_evidence=pin(D/'source_factory_evidence_221.json'),
    helper_test_cases=40,helper_pytest_seconds=4.31,helper_outer_seconds=12.063,
    helper_independent_findings_closed=False,actual_Bridge_footer_integrated=False,
    common_binder_authorizes_reads=False,stable_science_and_phase_receipt_design_correction_implemented=False,
    next_step='Review exact220 helper bytes; then source-specific factories, independent pinned B7 activation and Common per-read/phase route.',
    new_N0_Jobs_in_this_followup=0,real_native_calls=0,
    full_optimized_workflow_accepted=False,whole_workflow_performance_review_complete=False,
    formal_execution_ready=False,formal_run_authority=False,formal_result=False,
    resource_admission=False,native_execution_authorized=False,production_seal=False,official_review=False)
state_path=D/'pause_handoff_state_222.json';write_json(state_path,value)

previous=D/'acceptance_matrix_23.json';matrix=json.loads(previous.read_bytes())
matrix.update(observed_at_utc=now.isoformat(),predecessor_matrix=pin(previous),
    goal_status='paused',goal_complete=False,current_related_experiment_processes=processes,
    current_process_scope=value['process_observation_scope'],current_handoff=pin(handoff),
    current_paused_state=pin(state_path),current_common_typed_graph_checks=pin(D/'common_typed_graph_evidence_207.json'),
    current_standalone_provenance_evidence=pin(D/'callable_provenance_evidence_219.json'),
    current_standalone_factory_evidence=pin(D/'source_factory_evidence_221.json'),
    current_callable_factory_independent_findings_closed=False,current_common_route_authorized=False,
    current_roster_numerical_read_verified=False,
    current_consumer_pre_seal_conclusion='181 Core6 and202 named Core7/Roster5 scopes closed; unbound220 helpers await independent closure; numeric Roster/Common/fullchain open.',
    next_typed_substep=value['next_step'],
    full_optimized_workflow_accepted=False,whole_workflow_accepted=False,
    whole_workflow_performance_review_complete=False,formal_execution_ready=False,
    formal_run_authority=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
for row in matrix['acceptance']:
    if row['requirement']=='explicit typed Common integration graph':
        row.update(status='DRAFT_AST_canonical_import_and_fail_closed_rollback_verified_integration_open',
            evidence=[pin(D/'common_typed_graph_origin_205.json'),pin(D/'common_typed_graph_evidence_207.json')],
            remaining=['Independent pinned source-factory and real loader activation',
                'Provisional initial replay plus five original Common callsites',
                'Stable scientific report plus separate per-call phase receipt',
                'One Common-body phase window and independent numeric scopes'])
matrix['acceptance'].append(dict(requirement='standalone callable and source-factory provenance layer',
    status='DRAFT_40_units_terminal_verified_independent_findings_open',
    evidence=[pin(D/'callable_provenance_evidence_219.json'),pin(D/'source_factory_evidence_221.json')],
    scope='Canonical temporary modules only, no registry/lease/phase authority.',
    remaining=['Independent exact-byte audit','Source-specific imported-callable and generated-class checks',
        'Actual Bridge/Witness/Source/Common factories and fixed B7 manifest']))
out=D/'acceptance_matrix_24.json';write_json(out,matrix)
text=(f'{stamp} 暂停交接：原goal已paused，尚未完成；本次只保存状态，无新实验。\n'
    '旧chain07主体及独立后验04已完成，不重跑；实时Python/pytest/求解器进程快照见pause_handoff_state_222.json。\n'
    'Core6实际N0/oracle/数值重开181与Core7/Roster5命名范围202保留；数值Roster/Common/整链仍OPEN。\n'
    '207已验证20文件typed图AST、canonical import及拒绝路径rollback；215独立provenance16项通过，但未绑定B7。\n'
    '216断言通过而entry缺base失败，218归档断言失败均保留；219正确归档，未把216计作成功。\n'
    '220最新callable/source-factory小层40passed4.31s/outer12.063s/exit0、source unchanged、观察PID退出、句柄关闭；221九份精确归档。\n'
    '当前4份helper/test与221一致，但独立复核未闭合；真实Bridge/footer/activation/Common phase scope均未接入，B7 binder仍拒绝。\n'
    '208逐次phase ID写入stable validation report的要求有冲突：需另设phase_execution_receipt，由Witness同时绑定两者，尚未实现。\n'
    '下一步先审当前helpers，再接独立固定source factory/三种真实读入口和静态phase复用；不先消耗新N0或长链。\n'
    f'详细交接：continuation_handoff_20261019_pause.md；matrix24 SHA{pin(out)["sha256"]}。\n'
    '优化整链、整体性能预算和正式实验仍未验收；formal/native/resource各门false。\n\n').encode('utf-8')
for path,heading in ((H/'continuation_handoff_20261018.md','## 当前暂停交接\n\n'),
        (H/'performance_report.md','## 当前暂停进展\n\n'),(R/'docs/model_spec/blocker_register.md',''),
        (R/'docs/plan/科研项目执行步骤.md',''),(R/'docs/plan/H1_端到端里程碑验收_v1.md','')):
    old=path.read_bytes()
    if heading:updated=heading.encode('utf-8')+text+old
    else:
        first,separator,rest=old.partition(b'\n');assert separator
        updated=first+separator+b'\n'+text+rest
    path.write_bytes(updated)
print(json.dumps(dict(state=pin(state_path),matrix=pin(out),handoff=pin(handoff),
    processes=processes,core_202_matches=sum(row['matches_202'] for row in core_pins),
    typed_207_matches=sum(row['matches_207'] for row in graph_pins)),ensure_ascii=False))
