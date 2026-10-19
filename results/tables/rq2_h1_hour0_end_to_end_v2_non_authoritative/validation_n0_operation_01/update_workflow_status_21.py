"""Synchronize scoped consumer optimization evidence; preserve prior history."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path

H=Path(__file__).resolve().parent;R=H.parents[3];D=H/'whole_workflow_optimization_01_non_authoritative'
previous=D/'acceptance_matrix_20.json';v=json.loads(previous.read_bytes())
def evidence(name):
    path=D/name
    return dict(path=str(path.relative_to(R)),sha256=sha256(path.read_bytes()).hexdigest())
data=json.loads((D/'consumer_result_171.json').read_bytes())
obs=data['observations']['saved152_consumer_dag_observation.json']
assert data['terminal']['exit_code']==0 and data['terminal']['observed_owned_processes_absent'] and not data['pin_drift']
v.update(observed_at_utc=datetime.now(timezone.utc).isoformat(),
    predecessor_matrix=evidence(previous.name),current_related_experiment_processes=[],
    current_process_scope='169/170/171 observed PIDs absent with terminal exit0; no complete tree absence or ABA claim.',
    consumer_scope_implementation='Bootstrap6/Owned6/Verifier5 DRAFT;150 targeted cases, genuine empty header and saved152 diagnostic DAG verified.',
    current_consumer_pre_seal_input=evidence('consumer_pre_seal_input_173.json'),
    current_consumer_pre_seal_conclusion='independent named final findings pending',
    next_typed_substep='Finish independent named pre-seal findings, then one bounded Bootstrap6 synthetic N0 public return/receipt/close; Roster5 and connected typed graph remain open.',
    current_source_header=evidence('consumer_result_170.json'),
    monolithic_N0_public_return_verified=False,full_optimized_workflow_accepted=False,
    whole_workflow_performance_review_complete=False,formal_execution_ready=False,formal_run_authority=False,
    formal_result=False,resource_admission=False,native_execution_authorized=False)
for row in v['acceptance']:
    if row['requirement']=='N0 Bootstrap and roster growing-history cost':
        row.update(status='consumer_draft_units_empty_header_and_saved_DAG_verified_current_N0_and_Roster5_open',
            evidence=[evidence(name) for name in ('bootstrap5_retained_n0_bounded_result_152.json',
                'saved152_numerical_postcheck_result_153.json','saved152_readonly_reopen_result_154.json',
                'consumer_result_169.json','consumer_result_170.json','consumer_result_171.json')],
            remaining=['Current genuine Bootstrap6 public N0 return/execution receipt/close and saved-data postchecks.',
                'Actual Roster5 and three independent arms; typed Common/Genesis/Parent/Handoff/paired/Post/reopen.',
                'Whole workflow performance/resource budget and separate formal authority.'])
v['acceptance'].append(dict(requirement='method-bound consumer registry reuse and record retirement',
    status='DRAFT_local_evidence_verified_independent_named_findings_pending',
    evidence=[evidence(name) for name in ('consumer_result_169.json','consumer_result_170.json',
        'consumer_result_171.json','consumer_pre_seal_input_173.json')],
    scope='150 targeted cases include true partial-retire, producer/consumer retry,16-live-or-pending cap,foreign active capsule,owner GC and constructor composite primary. Current real empty header four read/phase scopes closed. Saved diagnostic operation DAG65.7726 to56.3763s,16full/16fresh/64contexts to8full/24fresh/64contexts, exact audit/decision bytes equal.',
    limitations=['Single fixed-order unprofiled saved diagnostic; genuine numerical public consumer timing and whole chain not measured.',
        'Original152 public return and graceful cleanup stay false;143 saved file names+bytes unchanged, empty-directory equality unproved.']))
out=D/'acceptance_matrix_21.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(v,stream,indent=2);stream.write('\n')
pin=sha256(out.read_bytes()).hexdigest();stamp=datetime.now().strftime('%Y-%m-%d %H:%M')
text=(f'{stamp} 开发状态：169/170/171均有exit0终态，已观察PID退出；旧chain07主体/后验04闭合，不重跑主体。\n'
    'Bootstrap6/Owned6/Verifier5消费者registry读窗已实现，仍为DRAFT_NONAUTHORITATIVE。每个constructor/inspect用原guard与fresh nonce，\n'
    '只在同一方法内复用confirmed proof，返回前close/取只读receipt/retire；16个全局live或pending槽与owner.close重试保留失败清理入口。\n'
    '169共150项通过46.04s/outer49.172s，覆盖真实partial retire、producer/consumer retry、上限、foreign active、GC与constructor primary组合。\n'
    '170当前源码真实空header创建/inspect/关闭/重开/inspect/关闭通过85.36s/outer90.078s，4个空读窗及phase窗完整关闭，0N0/Job/native。\n'
    '171保存152数据的单次固定顺序无profiler对照：原DAG65.7726s→两段consumer-sized operation56.3763s，局部少14.3%；\n'
    '16full/16fresh/64contexts→8full/24fresh/64contexts，八份audit/decision bytes一致，原oracle SHA2648f795…；1521pins及143保存文件名/字节无漂移。\n'
    '该诊断未测真实数值public consumer或整链耗时；152原public返回/原进程graceful cleanup仍false，153/154保存记录补验不改写该终态。\n'
    '173独立定向PRE_SEAL复核结论待返回；下一步174新版本单合成N0的public return/receipt/close诊断，固定400s预算已登记，尚未启动。\n'
    'Roster5/三臂/Common/Genesis/Parent/Handoff/paired/Post/reopen与完整优化整链、正式实验均未验收。\n'
    f'matrix21 SHA{pin}；所有formal/native/resource门保持false。\n\n')
documents=((H/'continuation_handoff_20261018.md','## 当前续作\n\n'),
    (H/'performance_report.md','## 当前性能进展\n\n'),(R/'docs/model_spec/blocker_register.md',''),
    (R/'docs/plan/科研项目执行步骤.md',''),(R/'docs/plan/H1_端到端里程碑验收_v1.md',''))
plan=json.loads((D/'bootstrap6_retained_n0_bounded_plan_174.json').read_bytes())
assert all(str(path) not in plan['files_sha256'] for path,_ in documents)
for path,heading in documents:
    original=path.read_text(encoding='utf-8')
    if heading:updated=heading+text+original
    else:
        first,rest=original.split('\n',1);updated=first+'\n\n'+text+rest.lstrip('\n')
    path.write_text(updated,encoding='utf-8',newline='\n')
print(json.dumps(dict(matrix=str(out),sha256=pin,documents=len(documents))))
