# H1 逐小时保存报告 parent 开发

状态：R3 DRAFT_NONAUTHORITATIVE；根唯一写入，独立只读开发审查。实现位于 `experiments/h1_saved_source_parent_development_v1.py`，复用已封存的 source binding、v3 hour archive 和 full attempt anchor；没有修改或增加旧 `src` 闭包成员。

## 范围与验收

该 parent 接收已保存的 raw reports。每个 public inspection/step 均进入已有 `solver_calls_forbidden` 上下文；没有 Job spawn、lease 消费或 native 入口。它为后继完整 parent 验证 source/carry 与父记录语义，独立逐 hour Job 接线仍待完成。

- 声明精确整数 `hours∈[1,192]`，每小时 stage inventory 由静态网络确定；完整 pinned RTS 条件下为 232×192=44544 个槽位。槽位声明不是执行次数或资源准入。
- source declaration 只由固定 origin 加当前 completed hour 得到，同时推进 power/workload raw index。每次从 pinned source 重建 current receipt，核验完整 identity、network 和 audit bytes。业务模型只接当前 row、raw workload、相对时钟与前 carry。
- 相邻来源保持 power/workload chain、package manifest、grid manifest、time basis 和一小时 timestamp 间隔。缺失来源保持 unresolved 并停止，不依据异常文字把缺尾改判为失败、成功或数学不可行。
- hour0 的 before 由既有 origin 规则生成。hour h>0 的 carry 只来自前一完整 accepted child 的独立重放 projection，核验 exact type、request key、before identity、完整 lock 数、network 与 completed_hours。调用者没有提供 carry 的入口。
- 先记录并锚定 parent intent（source pin、audit原文/hash、packet audit、before identity、request key、child path、stage slots），再消费 saved reports。child 完成后关闭并 fresh reopen，重载 parent 的全部来源与前缀后才能写 outcome。
- 每小时最多 intent/outcome 两事件；完整192h最多384 events和385 anchor records。所有文件保留，readback/anchor/source/replay异常使 owner poison。pending child 无恢复/重试入口；reopen 只读，必须提供独立 retained anchor pin。
- accepted/rejected 是保存报告的开发重放状态。科学判定仍由既有 v3 replay 执行，保留已批准的小负 generation 映射规则。旧小时 raw 在后续小时须重新接受真实模型/状态核验，不能复制 origin 作为 future witness。

## 必须保留的边界

这不是生产 worker 或 native parent，`independent_hour_jobs_integrated`、`producer_coverage_proven`、`resource_admission`、`formal_execution_ready`、`formal_result` 均为 false。`solver_calls=0` 指本 parent 的保存数据操作；不改写 raw 的原始 solver 字段。

目前复用的 v3 hour archive 在数值审计后存档；尚未把新的 raw ingress 接入这个 parent。解析/审计内部异常时，父 intent 保留并停止，但不能因此声称故障 raw 已完整落盘。后继需接入 raw-before-audit 和计时，计入额外副本及 metadata、SQLite、物理分配、scratch 和 reserve，不能继承旧磁盘准入。

所有前缀 fresh 检查保证当前文件系统可见的一致性；没有 hostile ABA、防恶意全链重写、卷级断电持久性或全局跨 namespace 排他保证。完整来源读取和反复 replay 的资源尚未计量，不作性能承诺。

## 开发验证矩阵

真实小型 saved chain：origin fresh reopen；hour0 raw 在 hour1 被真实 replay 拒绝；错误 pin/未来 pin/head；source chain 与时钟变化；缺尾不消费 child；不完整/额外 raw；intent、reader、outcome、anchor 失败窗口；poison、无 retry、reopen 只读。

192h 合成边界检查只证明 source/carry/parent 状态机的接口范围；若使用 test-only child seam，须显式记录，不作232阶段未来 producer 覆盖或科研 witness 证明。完整 pinned RTS 槽位算术沿用现有 shape 证据；真实192h连续求解、独立hour Job、全任务计时与资源准入仍开放。

测试终态、开发审查 findings 和保全核验须记录在新 non-authoritative development_checks 中。开发审查闭合不产生 official verdict 或新运行许可。
