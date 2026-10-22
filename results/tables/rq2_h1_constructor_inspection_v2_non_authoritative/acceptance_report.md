# Constructor inspection 后继开发记录

2026-10-21，R3 / DRAFT_NONAUTHORITATIVE。当前完成了一个 source 性能候选的窄验证、保存三小时身份绑定重构和一小时前缀净路径对照。原 owner 尚未接入，完整 168h/≤24h 整链预算与 episode terminal/reopen 仍待完成。

新增 capture helper、historical batch v2、exact source batch v2 和 detached data validator。每个新 Reader 取回构造器唯一一次完整 inspect 的原返回对象，保留原后置文件/source/prefix观察、两个独立 Reader 和异常关闭路径。生命周期固定 sentinel、creator、helper/MRO/callable 状态；不跨 operation 保存 source/current/registry 结果。旧实现与保存 case 均保留。

| 已执行检查 | 终态与作用域 |
|---|---|
| unit_04 | 110 passed / 3.03s，outer 6.390s；1306 pins 未变，观察 PID 退出。fake parent/列明故障窗口及 actual ordered-close 程序配合 stand-in owners，不是实际 source 文件故障证明 |
| oracle_01 | H3/M5 新完整双 Reader batch 93.285154s，worker 94.431699s，outer 97.985s；两个 Reader 各一次 parent traversal，21 个辅助数据拒绝通过，1308 pins 未变 |
| short_comparison_01 | H1/M5 固定 old→new 各一次完整双 Reader batch，57.131095s → 27.815387s；完整科学摘要、decision、frame/origin/action/Fraction 及允许 provenance 差异外的 audit 一致；outer 92.125s，1308 pins 未变 |
| comparison_01 | 最初四调用诊断在首个 old batch 返回前触发120s no-progress，outer120.328s/child exit15，0个完整call、无worker terminal。原件保留；独立 after 核验通过，不提供科学或性能结论 |

H1 对照本次少29.315709s（约51.3%），仅为单一固定顺序、每实现一测的保存前缀观测，不代表统计稳健收益、192h或生产时长。对照包含各自 identity、双 Reader、materialization、source/registry fresh 和 cleanup；没有 static identity memo，但保留 saved manifest-pin resolver seam，未重建或复审真实 manifest sources。

H3 oracle 使用保存 normal audit、fresh synthetic source/registry 和原 join/projection 重构 canonical scientific bytes，与 successor bytes 相同且 SHA 匹配保存的 predecessor scientific identity。没有读取 predecessor raw scientific payload，也不是独立科学实现。原输出字段的精确解释见 [oracle_01_interpretation.json](oracle_01_interpretation.json)；packet projection 单字段为明确 stand-in。H1 对照另执行原 batch 并与后继直接核对。

两个成功诊断各自核对465个 case/444个 owned 文件 SHA，观察 PID 均退出；新增 normal Job、selector/native 为0。原unit_01/02/03及失败attempt保留各自tested_bytes，不将测试数累加成新的覆盖量。实际读取保存了3模拟小时和1小时前缀，没有执行168/192h连接。

独立 PRE_SEAL 已促成局部 alias/callable、sentinel/creator、close程序和诊断预算修正；这是开发复核，不是 official verdict。真实 constructor→bookend 文件/metadata/非确定性/适用依赖故障等价、完整 dynamic closure/ABA、实际资源释放与 owner 接线仍未获证。candidate 尚未采纳；预算允许后续验证后采用，也允许拒绝候选并为 baseline/其他合法路径取得完整预算。

整链预算更新见 [whole_workflow_budget_status_v3.md](whole_workflow_budget_status_v3.md)。正式准备清单为 [formal_preparation_state_v3.json](formal_preparation_state_v3.json)，是当前对账草稿，保留1900-cell合同和全部支持，不替代自包含 successor preregistration、资源准入或运行权限。

本范围的 `formal_result`、`formal_execution_ready`、`resource_admission`、`native_execution_authorized`、`long_connected_launch_admitted`、完整192h/真实phase terminal/reopen、production seal及official review均为false。下一步先闭合 source 路径的适用故障/依赖证据，再按整链调用DAG完成代表性wall/RSS/storage与事件/holder容量登记，然后推进真实phase/episode连接。
