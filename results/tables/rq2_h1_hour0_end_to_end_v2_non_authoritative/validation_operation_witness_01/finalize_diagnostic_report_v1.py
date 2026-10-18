"""Publish a local development checkpoint from closed diagnostic evidence only."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
comparison_path=HERE/'saved_pair_comparison_01.json'
comparison=json.loads(comparison_path.read_bytes())
for name,h in comparison['evidence_sha256'].items():
    if sha256((REPO/name).read_bytes()).hexdigest()!=h:raise ValueError('diagnostic evidence drift')
original=json.loads((HERE.parent/'chain_07/request.json').read_bytes())['before']
if any(sha256((REPO/name).read_bytes()).hexdigest()!=h for name,h in original.items()):
    raise ValueError('original chain_07 source pin drift')
preseal=dict(schema='h1_operation_historical_diagnostic_preseal_summary_v1',
    status='DRAFT_NONAUTHORITATIVE',observed_at_utc=datetime.now(timezone.utc).isoformat(),
    review_scope='single fixed saved arm historical-only pair, unit and monitor helper evidence',
    independent_read_only_reviewer='/root/restart_review',
    findings_closed_for_diagnostic_scope=True,remaining_scoped_findings=[],official_verdict=None,
    diagnostic_manifest_sha256=comparison['diagnostic_manifest_sha256'],
    comparison_sha256=sha256(comparison_path.read_bytes()).hexdigest(),
    postcheck_source_sha256=sha256((HERE/'postcheck_saved_pair_v1.py').read_bytes()).hexdigest(),
    original_chain_07_source_files_unchanged=len(original),
    full_chain_passed=False,production_handoff_integrated=False,whole_workflow_performance_review_complete=False,
    long_chain_launch_admitted=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
with (HERE/'preseal_summary_01.json').open('x',encoding='utf-8') as stream:json.dump(preseal,stream,indent=2)
full=comparison['summary']['full_only'];operation=comparison['summary']['operation']
report=f'''# 单操作 historical numerical witness 有界对比

2026-10-17，DRAFT_NONAUTHORITATIVE。此为里程碑2的重复校验诊断，不是完整链验收或正式实验。

同一个 chain_06 network-only N0，在两个新进程中分别运行一次原v1 oracle、两次diagnostic prepare。
每mode仅一次，固定300秒、512MiB sampled process-tree RSS、64MiB新工件上限。使用相同显式解释器
路径及code/metadata parse leases；oracle和每次prepare前分别重置parse window，stock distribution
discovery每次执行。未使用static identity shortcut；真实native调用为0（固定solver-forbidden路径）。

| 观测 | full-only | operation reuse |
|---|---:|---:|
| prepare1秒 | {full['prepare_seconds'][0]:.6f} | {operation['prepare_seconds'][0]:.6f} |
| prepare2秒 | {full['prepare_seconds'][1]:.6f} | {operation['prepare_seconds'][1]:.6f} |
| 两次prepare合计秒 | {full['two_prepare_seconds']:.6f} | {operation['two_prepare_seconds']:.6f} |
| 实际full numerical inspections | 8 | 4 |
| 原始context evaluations | 32 | 32 |
| sampled peak RSS bytes | {full['observed_peak_rss_bytes']} | {operation['observed_peak_rss_bytes']} |
| 新工件bytes | {full['observed_new_artifact_bytes']} | {operation['observed_new_artifact_bytes']} |

第二次prepare减少{comparison['second_prepare_fraction_saved']:.4%}，两次合计减少
{comparison['two_prepare_fraction_saved']:.4%}。这是一个固定输入的单对结果，不是统计分布或完整链耗时估计。
第一次的四次full检查仍执行；第二次为八次数值证明复用，依旧进行十六次原始context观察。

两mode的783项source/package/test/evidence pins与461个保存文件一致，旧科学decision/audit exact一致。
模式、ordinal、实际full/within-prefix/cross-prepare/context次数、proof role、随机session、proof basis、
envelope与execution receipt hashes均闭合。各自33把保存锁可重获释放；已观察的owned PID+creation-time
进程树为空，RSS仅为采样观测。postcheck在两次terminal后重新核对完整source与saved inventory。

unit_06为68passed（26.12秒），monitor_unit_02为3passed。
monitor测试固定完整outer SHA后执行其未改动AST helper，并实际验证child/grandchild清退、creation-time
误认拒绝和锁重获；此测试本身不代表完整CLI或saved诊断通过。两个saved模式另有各自真实终态。
独立只读PRE_SEAL复核未见本诊断范围的剩余finding；不构成official verdict。

确切包：`diagnostic_source_manifest_v1.json`，SHA `{comparison['diagnostic_manifest_sha256']}`。
主证据：`saved_pair_comparison_01.json`、两个mode的outer/inner `terminal.json`、`request.json`、
`operation_receipt.json`及每次prepare记录。所有早期草稿、失败/旧字节检查保留，不替代本次固定字节。
原chain_07的36项启动source pins不变；未对旧进程发出停止、重启或恢复命令。

## 下一出口

候选尚未接生产exact-source/common/Handoff。生产必须先绑定真实Handoff token、guard全集与三arm独立槽，
并等完整exact-source/common返回成功、source与第二registry/末次观察/结果构造完成后才激活证明，
覆盖callback/cleanup/return故障和close/reopen replay，随后取得真实handoff slice耗时。
当前复用后的第二次prepare仍需19.47秒，不能假定去掉数值重算就解决全部成本。

慢missing-one拒绝分支保留完整key集合，`None`在unresolved disposition合法，因此不采用any-None提前拒绝。
详见`optimization_decisions_01.json`。完整hour-0、192h、整体性能准入、资源准入、seal/official review与
正式运行各门仍OPEN，未启动新长链。
'''
with (HERE/'performance_report.md').open('x',encoding='utf-8') as stream:stream.write(report)
print(json.dumps(dict(comparison_sha256=preseal['comparison_sha256'],original_chain_07_source_files_unchanged=len(original),
    local_two_prepare_fraction_saved=comparison['two_prepare_fraction_saved'],formal_result=False)))
