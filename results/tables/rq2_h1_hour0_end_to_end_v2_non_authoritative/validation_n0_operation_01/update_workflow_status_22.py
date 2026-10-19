"""Record actual single-N0 closure and open downstream integration boundaries."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import psutil

H=Path(__file__).resolve().parent;R=H.parents[3];D=H/'whole_workflow_optimization_01_non_authoritative'
previous=D/'acceptance_matrix_21.json';v=json.loads(previous.read_bytes())
def evidence(name):
    path=D/name
    return dict(path=str(path.relative_to(R)),sha256=sha256(path.read_bytes()).hexdigest())
for name in ('bootstrap6_retained_n0_bounded_result_174.json','saved174_postcheck_result_176.json','saved174_postcheck_result_177.json'):
    data=json.loads((D/name).read_bytes());assert data['terminal']['exit_code']==0
    assert data['terminal']['observed_owned_processes_absent'] and not data['terminal']['cleanup_errors']
    for proc in data['terminal']['observed_owned_processes']:
        try:assert abs(psutil.Process(proc['pid']).create_time()-proc['creation_time'])>1e-6
        except psutil.NoSuchProcess:pass
v.update(observed_at_utc=datetime.now(timezone.utc).isoformat(),predecessor_matrix=evidence(previous.name),
    current_related_experiment_processes=[],
    current_process_scope='All observed174/176/177/180 PIDs absent; no complete process-tree absence or ABA claim.',
    current_bootstrap6_actual_public_N0_return_and_close_verified=True,
    current_bootstrap6_original_numerical_oracle_verified=True,
    current_bootstrap6_genuine_numerical_consumer_reopen_verified=True,
    current_bootstrap6_exact_planned_invocation_metadata_matched=False,
    current_bootstrap6_plan_metadata_exception=evidence('bootstrap6_plan_metadata_mismatch_175.json'),
    current_consumer_pre_seal_conclusion='173 implementation named findings closed;181 actual-run/postcheck and exception review pending.',
    current_implementation_scoped_findings=evidence('consumer_scoped_findings_173.json'),
    current_actual_postcheck_input=evidence('bootstrap6_postchecks_pre_seal_input_181.json'),
    next_typed_substep='Definition-bound authenticated foreign consumer registry route and Roster/Common integration in versioned successors; keep Core6 and saved174 source lineage fixed.',
    monolithic_N0_public_return_verified=False,legacy152_original_public_return_verified=False,
    full_optimized_workflow_accepted=False,whole_workflow_performance_review_complete=False,
    formal_execution_ready=False,formal_run_authority=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
for row in v['acceptance']:
    if row['requirement']=='N0 Bootstrap and roster growing-history cost':
        row.update(status='actual_Bootstrap6_single_N0_and_saved_postchecks_verified_plan_metadata_exception_preserved',
            evidence=[evidence(name) for name in ('bootstrap6_retained_n0_bounded_result_174.json',
                'bootstrap6_plan_metadata_mismatch_175.json','saved174_postcheck_result_176.json','saved174_postcheck_result_177.json')],
            scope='Actual v6 public return/receipt/close, original oracle and genuine constructor/inspect saved replay verified.174 launch plan retains wrongv5 module/old136 header scalars, so exact plan provenance match remainsfalse.',
            remaining=['Authenticated foreign consumer read/borrow/callback routes and Roster5.',
                'Three independent arms; typed Common/Genesis/Parent/Handoff/paired/Post/reopen.',
                'Complete workflow performance/resource budget and separate formal authority.'])
    elif row['requirement']=='method-bound consumer registry reuse and record retirement':
        row.update(status='DRAFT_implementation_named_findings_closed_actual_numerical_reopen_verified',
            evidence=[evidence(name) for name in ('consumer_scoped_findings_173.json','consumer_result_171.json',
                'saved174_postcheck_result_177.json','bootstrap6_postchecks_pre_seal_input_181.json')],
            scope='173 named lifecycle/primary/retirement findings closed.177 genuine current numerical constructor/inspect total8full24fresh64contexts,2distinct private sessions,2closed phase windows,154 saved files unchanged.',
            limitations=['Public read method counts are measured, but no matched whole-chain runtime comparison.',
                '174 actual successful source lineage retained with its planning metadata exception;181 review pending.'])
v['acceptance'].append(dict(requirement='diagnostic test secondary reporting successor',status='targeted_AST_successor_verified',
    evidence=[dict(path=str((H/'n0_diagnostic_primary_successor_units_180/terminal.json').relative_to(R)),
        sha256=sha256((H/'n0_diagnostic_primary_successor_units_180/terminal.json').read_bytes()).hexdigest()),
        evidence('bootstrap6_postchecks_pre_seal_input_181.json')],
    scope='Future test5 only adds nested reporting protection; five extracted original-handler normal/cleanup/throwing-repr/throwing-note/success checks.0newJob.174 originalv4 and179 nonzero entry evidence preserved.'))
out=D/'acceptance_matrix_22.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(v,stream,indent=2);stream.write('\n')
pin=sha256(out.read_bytes()).hexdigest();stamp=datetime.now().strftime('%Y-%m-%d %H:%M')
text=(f'{stamp} 当前续作：已观察174/176/177/180进程均退出；旧chain07主体/后验04闭合，不重跑。\n'
    '174实际Bootstrap6单N0 public return/原执行receipt/owner close通过，1passed351.02s/outer356.813s；Job exit0/quiescent50.453s。\n'
    '8retention/4full28fresh64contexts/17phase段/constructor读窗均关闭，pending0/1380pins无漂移/10locks重取释放。\n'
    '175保留plan两处遗留：invocation.module=v5、current_header指旧136；actual test/JUnit/import/public return均v6，exact计划参数/来源匹配仍false。\n'
    '176原oracle保存补验通过80.01s/outer86.578s；177真实数值只读重开/inspect/close通过170.90s/outer175.718s。\n'
    '177两独立method scopes各4full12fresh32contexts，总8full24fresh64contexts，2phase窗关闭；两项各1542pins及154保存文件名/字节不变，0newJob/native。\n'
    '173实现定向findings已闭合；181实际run/postcheck/metadata例外复核待返回。future test5的secondary repr/add_note保护经180五项0.40s/outer2.719s验证，未再跑N0；\n'
    '179的5逻辑pass但entry因未创建base而非零，旧v4和该失败原件保留。\n'
    '171局部DAG固定顺序65.7726→56.3763s（少14.3%）不外推整链；152旧调用return/cleanup仍false。\n'
    '下一瓶颈是Roster/Common持原owner guard且nonce=None的foreign消费者；Core6仅有constructor/inspect固定读入口，不能借producer nonce或detached receipt。\n'
    '先设计定义期绑定的后继消费者路线，保持已验Core6/174源码不改，再接Roster/三臂/Common/Genesis/Parent/Handoff/paired/Post/reopen与完整预算。\n'
    f'matrix22 SHA{pin}；优化整链和正式实验未验收，所有formal/native/resource门false。\n\n')
for path,heading in ((H/'continuation_handoff_20261018.md','## 当前续作\n\n'),
        (H/'performance_report.md','## 当前性能进展\n\n'),(R/'docs/model_spec/blocker_register.md',''),
        (R/'docs/plan/科研项目执行步骤.md',''),(R/'docs/plan/H1_端到端里程碑验收_v1.md','')):
    original=path.read_text(encoding='utf-8')
    if heading:updated=heading+text+original
    else:
        first,rest=original.split('\n',1);updated=first+'\n\n'+text+rest.lstrip('\n')
    path.write_text(updated,encoding='utf-8',newline='\n')
print(json.dumps(dict(matrix=str(out),sha256=pin,documents=5)))
