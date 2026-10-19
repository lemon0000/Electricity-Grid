"""Synchronize current terminal evidence while preserving historical records."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
D=HERE/'whole_workflow_optimization_01_non_authoritative'
previous=D/'acceptance_matrix_19.json';value=json.loads(previous.read_bytes())
def evidence(name):
    path=D/name
    return dict(path=str(path.relative_to(ROOT)),sha256=sha256(path.read_bytes()).hexdigest())

read=json.loads((D/'saved152_readonly_reopen_result_154.json').read_bytes())
assert read['terminal']['exit_code']==0 and read['terminal']['observed_owned_processes_absent']
assert not read['terminal']['cleanup_errors']
value.update(observed_at_utc=datetime.now(timezone.utc).isoformat(),
    predecessor_matrix=dict(path=str(previous.relative_to(ROOT)),sha256=sha256(previous.read_bytes()).hexdigest()),
    current_related_experiment_processes=[],
    current_process_scope='All observed diagnostic PIDs are absent; no complete process-tree absence or ABA claim.',
    current_pre_seal_review=evidence('canonical_path_entry6_scoped_findings_151.json'),
    next_typed_substep='Implement/audit fresh consumer-bound registry read scope in versioned successors, then current public N0 lifecycle and connected typed graph.',
    current_source_header=evidence('roster4_header_probe_result_136.json'),
    monolithic_N0_public_return_verified=False,
    saved_N0_numerical_and_readonly_reopen_verified=True,
    fixture_metadata_extension='retired_not_adopted; no observed ROI, two open findings preserved; not used by entry6',
    new_consumer_scope_design=evidence('consumer_registry_read_scope_design_155.md'))
for row in value['acceptance']:
    if row['requirement']=='N0 Bootstrap and roster growing-history cost':
        row.update(status='current_header136_complete_saved152_oracle153_reopen154_verified_monolithic_return_open',
            evidence=[evidence(name) for name in ('roster4_header_probe_result_136.json',
                'bootstrap5_retained_n0_bounded_result_152.json','saved152_numerical_postcheck_result_153.json',
                'saved152_readonly_reopen_result_154.json')],
            scope='152 current synthetic Job49.281s/exit0; original public call stopped300.25s. Eight external heads persisted before callbacks;119 candidate files preserved.153 numerical oracle equal;154 current Bootstrap5 readonly constructor/inspect/close passed with both external heads,2 complete phase windows,0newJob/native and143 saved files unchanged.',
            remaining=['Original public bootstrap return, execution receipt and graceful complete lifecycle.',
                'Fresh consumer registry proof reuse and actual Roster5 shadow/borrow integration.',
                'Three independent N0 arms and genuine typed Common/Genesis/Parent/Handoff/paired/Post/reopen.',
                'Complete workflow performance/resource budget, formal readiness and authorization.'])
    elif row['requirement']=='public phase segment identity and failure semantics':
        row.update(status='named_scoped_findings135_closed_current_header136_verified',
            evidence=[evidence('public_phase_scoped_findings_135_reconfirmed_149.json'),
                      evidence('roster4_header_probe_result_136.json')])
value['acceptance'].extend([
    dict(requirement='fixture metadata scope expansion',status='retired_not_adopted',
         evidence=[evidence('fixture_metadata_diagnostic_result_145.json')],
         scope='84.22s vs83.50s prior saved numerical test; no observed benefit. Exact143/145 bytes archived; unresolved findings are not used downstream.'),
    dict(requirement='existing canonical path helper diagnostic composition',status='local_diagnostic_and_named_failure_scope_verified',
         evidence=[evidence('saved137_path_diagnostic_result_148.json'),evidence('canonical_path_entry6_scoped_findings_151.json'),evidence('saved152_readonly_reopen_result_154.json')],
         scope='148 fixed-order cProfile outer153.984 to134.75s, same science/counts.15010 child tests cover reader/primary,close false/raise/persistent andCLI.151 named findings closed. Current entry6 exercised in153/154; no full-chain performance claim.'),
    dict(requirement='saved current N0 numerical and readonly owner replay',status='verified_saved152_data_and_current_Bootstrap5_reopen',
         evidence=[evidence('saved152_numerical_postcheck_result_153.json'),evidence('saved152_readonly_reopen_result_154.json')],
         scope='Independent observation using original numerical algorithm; new readonly owner cleanly closed. Original152 producer return/cleanup remain unverified.')])
target=D/'acceptance_matrix_20.json'
with target.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
pin=sha256(target.read_bytes()).hexdigest()
stamp=datetime.now().strftime('%Y-%m-%d %H:%M')
text=(f'{stamp} 开发状态：当前已观察的诊断进程均退出；旧chain07主体与独立后验04已闭合，主体不重跑。\n'
    '136当前Bootstrap5/Roster4 header完整通过；135身份/线程/首次entry故障的定向findings已闭合。\n'
    '145夹具metadata扩展无收益，已停止采用；148原CanonicalPathLease局部诊断outer153.984→134.75s，\n'
    '仅单次固定顺序cProfile对照，不能外推整链。150入口失败/CLI十项通过，151定向findings闭合。\n'
    '152单N0诊断在300.25s停止：Job exit0/quiet49.281s，8份外部heads在callback确认前落盘；\n'
    '原public bootstrap返回、完整执行receipt和原进程graceful cleanup仍未验证，不能改写成成功。\n'
    '153保存候选原数值oracle哈希一致，outer90.032s；154用外部heads只读重开当前Bootstrap5，\n'
    'inspect确认pending_post_N并关闭，outer176.594s；2个phase窗完整关闭、1512pins及143保存文件无漂移，\n'
    '新增Job/native=0。该新owner的成功关闭不替代152原调用终态。当前完整优化整链/正式实验均未验收。\n'
    '下一瓶颈为消费者registry重复full-only校验；design155固定新版本与同一方法内复用边界，尚未实现。\n'
    f'matrix20 SHA{pin}；所有formal/native/resource门保持false，见whole_workflow_optimization_01_non_authoritative。\n\n')
for path,heading in ((HERE/'continuation_handoff_20261018.md','## 当前续作\n\n'),
        (HERE/'performance_report.md','## 当前性能进展\n\n'),
        (ROOT/'docs/model_spec/blocker_register.md',''),
        (ROOT/'docs/plan/科研项目执行步骤.md',''),
        (ROOT/'docs/plan/H1_端到端里程碑验收_v1.md','')):
    original=path.read_text(encoding='utf-8')
    if heading:path.write_text(heading+text+original,encoding='utf-8',newline='\n')
    else:
        first,rest=original.split('\n',1)
        path.write_text(first+'\n\n'+text+rest.lstrip('\n'),encoding='utf-8',newline='\n')
print(json.dumps(dict(matrix=str(target),sha256=pin,documents=5)))
