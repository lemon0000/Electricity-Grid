# 分层接入—通知—Checkpoint候选方案核查

2026-11-09。研究设计评估，非已验证贡献；未启动新实验。

## 判断

可以作为下一候选问题，但目前不能称实证最强或已证明优于强基线。核心应是：不同接入阶段，可中断容量和通知/响应条件下，哪些任务接纳与运行承诺能持续满足原SLA？输出firm容量—通知条件—可接纳业务的可行边界，并检验checkpoint执行状态是否改变阶段决策。

## 来源核查与必要修正

- [NGED官方alternative connections](https://connections.nationalgrid.co.uk/alternative-connections)支持需求/发电侧替代接入，可为等候工程完工的临时安排，也可长期存在，具体削减条件按connection offer。不能把所有Flexible协议视为必然Firm-later。
- [NGED官方Flexible Connection Options](https://www.nationalgrid.co.uk/downloads-view-reciteme/540250)支持import/export控制和LIFO；排队原则针对受相同约束影响的连接，不能未经具体合同直接推定同一园区的新增设备批次处于LIFO栈顶。
- [ERCOT 2026-09官方通知](https://www.ercot.com/services/comm/mkt_notices/M-A090226-01)描述SB6不同法律条款及拟议运行框架；[SB6正式文本](https://capitol.texas.gov/tlodocs/89R/billtext/html/SB00006F.htm)包含某类服务至少24小时通知条款。不能将5分钟SCED周期直接写成所有SB6大型负荷紧急调用的5分钟提前量；须明确服务、主体、协议及版本。
- [Williams硬件示范](https://arxiv.org/html/2606.25098v1)中的15分钟graceful ramp不是所有任务checkpoint损失阈值。响应完成时限、提前通知、ramp和checkpoint完成时间分别建模。
- [ASI Appendix D](https://arxiv.org/html/2609.05406v1)明确checkpoint interval与恢复吸收率为illustrative contract parameters；不能把1h间隔、10%吸收率或12.5%额外损失当实测。
- Flex 0–3的具体数值本轮只定位到行业二手说明，未定位为EPRI正式统一SLA标准。Flex1允许某幅度slowdown持续3–6h不等于每任务可延期3–6h；cyclic backlog 24h界也不是每任务24h原期限。
- 500MW/154–326MW为PJM报告案例，NGED为英国合同，ERCOT为美国另一制度。可作分别有来源的情景族，不能拼称一个真实站点的已观测合同闭环。

## 正确的物理状态

任务状态至少包括剩余有效工作、距最近成功checkpoint的未保存进度、保存/重启状态、原期限及允许控制方式。损失取决于这些状态和“通知提前量＋允许响应时间”内能否完成安全暂停，不能固定为notice<15min即损失。

功率削减可通过限功率、迁移、暂停或终止获得；只有某类强制终止才一定涉及未保存进度丢失。预先checkpoint可能有写盘时间/能耗和吞吐损失，也必须计入。若原功率映射仍是P=b+ax，逐小时物理不等式的仿射压缩仍成立，新增的是有状态服务可行性，不能声称标量供电上限本身错误。

## 比较设计

1. 仅看时变供电上限：诊断对照，说明省略内部服务状态的风险。
2. 保留checkpoint状态、原期限与通知信息的标准因果调度：必要强基线，检验所谓stage-aware优势是否只是比对方多看信息/约束。
3. 同任务同事件同合同的完整小规模优化参考：检查可行边界或保守程度。若标准调度已实现相同承诺，不能宣称新算法改善；仍需看是否得到新且有价值的合同设计结论。

所有方法同信息集；不得让本方法提前知道未来调用而基线到事件发生才获知。接入合同并非把特定任务物理接到Firm/Flex电源；Tier匹配是保证可削减额度的内部组合管理。

## 验证关口

先用独立来源明确的单一合同族；SLA/保存耗时缺测则清楚标为情景，不估计实测违规率。固定两个任务状态总MW/剩余工作相同，仅checkpoint readiness不同，检验notice变化是否改变同一响应的履约；再检验该差异是否改变阶段可接纳业务或所需firm容量。

若checkpoint可零成本瞬时完成、任务原本不需要终止、或供电/清洁余量始终宽松，效应应减弱或消失。若差异只在弱基线出现，应按相应范围报告，停止“新调度方法”主张。任何严重/级联违约的量级都需要数据或固定模型证据，不能在实验前预设。
