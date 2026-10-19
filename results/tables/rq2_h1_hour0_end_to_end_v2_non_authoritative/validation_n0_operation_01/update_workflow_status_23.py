"""Synchronize current scoped acceptance and remaining typed integration."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import psutil

H=Path(__file__).resolve().parent;R=H.parents[3];D=H/'whole_workflow_optimization_01_non_authoritative'
def evidence(name):
    path=D/name;return dict(path=str(path.relative_to(R)),sha256=sha256(path.read_bytes()).hexdigest())
previous=D/'acceptance_matrix_22.json';v=json.loads(previous.read_bytes())
for number in ('199','200','201'):
    current=json.loads((D/('roster_result_'+number+'.json')).read_bytes())
    for row in current['terminal']['observed_owned_processes']:
        try:assert abs(psutil.Process(row['pid']).create_time()-row['creation_time'])>1e-6
        except psutil.NoSuchProcess:pass
v.update(observed_at_utc=datetime.now(timezone.utc).isoformat(),predecessor_matrix=evidence(previous.name),
    current_related_experiment_processes=[],current_process_scope='199/200/201 observed PIDs absent; sampled process evidence only.',
    current_consumer_pre_seal_conclusion='181 actual Core6 run/postcheck scope and202 current Core7/Roster5 named scope closed; Common/numeric Roster remain open.',
    current_actual_postcheck_findings=evidence('bootstrap6_postchecks_scoped_findings_181.json'),
    current_roster_scoped_findings=evidence('roster_scoped_findings_202.json'),
    current_roster_empty_real_lifecycle_verified=True,current_roster_numerical_read_verified=False,
    current_common_route_authorized=False,current_common_typed_draft_origin=evidence('common_typed_graph_origin_205.json'),
    next_typed_substep='Pinned bridge/witness/Common provenance, loader activation and provisional method-initial replay routes; then numeric Roster and connected chain budget.',
    full_optimized_workflow_accepted=False,whole_workflow_performance_review_complete=False,
    formal_execution_ready=False,formal_run_authority=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
for row in v['acceptance']:
    if row['requirement']=='method-bound consumer registry reuse and record retirement':
        row.update(status='DRAFT_Core7_Roster5_named_scope_closed_numeric_Roster_and_Common_open',
            evidence=[evidence('roster_scoped_findings_202.json'),*[evidence('roster_result_'+n+'.json') for n in ('199','200','201')]],
            scope='Current exact caller/invoke/body frame and callback protection, shared16 active/pending slots, retryable retirement, safe reporting, genuine empty reopen and phase-byte regressions.',
            limitations=['Numeric Roster public path and Common activation have not run.',
                'No source-valid unpinned bridge is authorized; typed successors remain drafts.',
                'Static proof reuse is confined to an immutable phase window; numerical proofs to each individual read scope.'])
v['acceptance'].append(dict(requirement='explicit typed Common integration graph',status='DRAFT_mechanical_namespace_schema_graph_created_unvalidated',
    evidence=[evidence('common_typed_graph_origin_205.json'),evidence('common_registry_integration_design_204.md')],
    scope='20 provisional files:18 new successors plus2 preexisting Common drafts; old source paths preserved.',
    remaining=['AST and import/loader rollback checks','Pinned independent provenance and lifecycle activation',
        'Provisional initial replay plus exact five Common callsites','One Common-body phase window with fresh per-replay scopes']))
out=D/'acceptance_matrix_23.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(v,stream,indent=2);stream.write('\n')
pin=sha256(out.read_bytes()).hexdigest();stamp=datetime.now().strftime('%Y-%m-%d %H:%M')
text=(f'{stamp} 当前续作：旧chain07主体及独立后验04已闭合，不重跑；当前199/200/201观察PID均退出。\n'
    '181已归档实际Core6单N0/原oracle/真实数值只读重开定向复核；174计划遗留module/header例外原样保留。\n'
    'Core7/Owned7/Verifier6/Roster5与phase-kernel2/binding4/operation2为DRAFT后继，未替换Core6或174保存字节。\n'
    '199当前36项通过54.38s/outer57.094s；200真实空头创建/检查/关闭/重开通过124.27s/outer129.093s，8phase窗+10空registry scope；\n'
    '201七项真实phase字节等价/失败段回归通过32.83s/outer35.687s。各source pins相符、观察PID退出、cleanup/storage错误0、原句柄关闭，0newN0/Job/native。\n'
    '202独立定向findings闭合caller/frame clone、callback-active阻断、共享16槽/退休重试和空头生命周期；18源码快照已保存。\n'
    '数值Roster与Common仍OPEN；Common binder当前显式拒绝。204设计要求预置source pins/blueprint、弱footer登记、loader独立activation、\n'
    'Genesis/Handoff两类一次性provisional initial replay及Common五个固定父帧/CALLsite，结束清强引用；拟每次Common共享一个无callback静态phase窗，数值scope逐replay独立关闭。\n'
    '205已创建20文件显式typed后继图（18新文件+2原有Common draft），旧路径保留，下一步静态/导入验证及桥路由实现；不先消耗新N0 Job。\n'
    '三臂/Common/Genesis/四Parent/Handoff/paired/Post/reopen、整体预算和正式实验仍未验收。\n'
    f'matrix23 SHA{pin}；所有formal/native/resource门false。\n\n')
for path,heading in ((H/'continuation_handoff_20261018.md','## 当前续作\n\n'),
        (H/'performance_report.md','## 当前性能进展\n\n'),(R/'docs/model_spec/blocker_register.md',''),
        (R/'docs/plan/科研项目执行步骤.md',''),(R/'docs/plan/H1_端到端里程碑验收_v1.md','')):
    original=path.read_text(encoding='utf-8')
    if heading:updated=heading+text+original
    else:
        first,rest=original.split('\n',1);updated=first+'\n\n'+text+rest.lstrip('\n')
    path.write_text(updated,encoding='utf-8',newline='\n')
print(json.dumps(dict(matrix=str(out),sha256=pin,documents=5)))
