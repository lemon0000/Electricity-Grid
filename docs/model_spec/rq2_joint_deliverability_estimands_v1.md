# RQ2 联合服务可交付前沿与归因指标 v1

> 状态：`SEALED_READY_FOR_INDEPENDENT_REVIEW`。机器可读科学协议见
> `configs/rq2_joint_deliverability_preregistration_v1.yaml`。本文件定义数学口径，
> 已完成pre-seal验收，不提供执行授权或正式结果。

## 1. 研究对象

固定网络安全所要求的逐时调用 \(g_t\)，逐级提高小时级 CFE 目标
\(\alpha\)，研究同一业务时序包络完成两项服务时所需的最低归一化柔性。

首篇论文的主问题为：

> 在网络安全调用保持为硬约束时，小时级 CFE 目标提高会怎样改变联合服务的
> 最低业务柔性需求；相对两项服务单独运行，联合时序交互及分离记账造成何种
> 有符号容量偏差？

公开 benchmark 的结论对象是完整 24 小时、zero-carry-in 窗口。模型同时约束
瞬时功率、持续时间、事件次数、累计能量、恢复功率和恢复债务。

## 2. 四臂比较

对每个注册参数 cell 和 CFE 目标 \(\alpha\)，使用相同输入、训练支持、时序
包络和 solver contract 计算：

| 符号 | arm | 含义 |
|---|---|---|
| \(D_N\) | `network_only_shared` | 只履行网络调用所需的最低柔性 |
| \(D_C\) | `cfe_only_shared` | 只履行小时级 CFE 调用所需的最低柔性 |
| \(D_J\) | `joint_correct_shared` | 两项服务共享真实时序包络时所需的最低柔性 |
| \(D_B\) | `joint_b6_separate_planning_shared_execution` | 两项服务分开进行时序记账时规划出的最低柔性 |

\(D_N,D_C,D_J,D_B\) 均以 \(D_{DC}\) 归一化。只有 arm 的最优性证书有效，
且代表点候选通过完整 training Cartesian support 审计时，\(D\) 才有定义。
若在注册上限 \(D=1\) 处被证明不可行，只报告
`proven_infeasible_at_registered_cap_estimand_undefined`，不把 1 当作估计值。
timeout、缺 incumbent 或证书不完整统一记为 `unresolved`。

## 3. 主归因恒等式

先定义两项单服务中更严格的一项：

\[
D_{\mathrm{single}}=\max(D_N,D_C).
\]

联合服务相对单服务瓶颈的有符号交互量为：

\[
I_{\mathrm{joint}}=D_J-D_{\mathrm{single}}.
\]

其中可进一步拆成：

\[
I_{\mathrm{sep}}=D_B-D_{\mathrm{single}},
\]

\[
A_{\mathrm{B6}}=D_J-D_B,
\]

\[
I_{\mathrm{joint}}=I_{\mathrm{sep}}+A_{\mathrm{B6}}.
\]

解释如下：

- \(I_{\mathrm{joint}}>0\)：联合履约比更严格的单服务需要更多柔性；
- \(I_{\mathrm{joint}}<0\)：共享轨迹通过事件合并等机制形成portfolio relief；
- \(I_{\mathrm{sep}}\)：B6分离包络相对单服务瓶颈的有符号交互；
- \(A_{\mathrm{B6}}>0\)：B6相对correct少配置柔性；
- \(A_{\mathrm{B6}}<0\)：B6相对correct多配置柔性。

完整时序模型包含持续时间、事件次数、minimum-event-power、休息、累计能量和
恢复状态，因此shared与separate tracks通常不构成集合嵌套。例如交错调用在共享
轨迹中可能合并为一个事件，却在两个分离轨迹中形成更多事件。因此不预设
\(D_B\le D_J\)，也不预设\(D_J\ge\max(D_N,D_C)\)。

冻结70-cell前序中唯一的`diagnostic_mixed` cell已出现
\(D_B=14.0217577>D_J=12.0\)，与上述非嵌套结构一致。该历史结果只用于排除错误
的顺序假设，不作为新46-cell前沿的确认性结论。

加法恒等式是machine gate。任何超过 \(10^{-6}\) 的违反都标记为协议、实现或
数值证书失败；四臂顺序本身是待观察结果。

## 4. 离散可交付前沿

若power block在\(\alpha=1\)时保存的CFE缺口为\(d^{CFE,1}_{it}\)，则重建
可再生份额

\[
s^{RE}_{it}=1-d^{CFE,1}_{it}.
\]

对目标\(\alpha>0\)，完整CFE服务请求为

\[
c_{ijt}(\alpha)=
\frac{\max\{\alpha-s^{RE}_{it},0\}}{\alpha}.
\]

该请求不截断到当小时`available_flexibility`；若业务资源不足，应由CFE-only
arm识别为单服务瓶颈。恢复功率上界为

\[
\bar r^{eff}_{ijt}(\alpha)=
\min\left\{
\bar r^{business}_{jt},
\max\left(\frac{s^{RE}_{it}}{\alpha}-1,0\right)
\right\}.
\]

这保证延期任务的恢复仍满足注册小时CFE目标。旧v6的
`min(CFE deficit, available flexibility)`请求和仅按业务空闲量计算的恢复headroom
不进入新46-cell实现。

源数据把\(s^{RE}\)截断在1，因此\(\alpha=1\)时注册的CFE-compatible surplus恒为
0。该点作为严格压力端点报告；若CFE-only已因恢复闭环不可行，应归为单服务瓶颈，
不能归因于联合交互。

注册 CFE 目标为：

\[
\alpha\in\{0.50,0.70,0.85,1.00\}.
\]

对每个 `flexible_fraction × normalized_recovery_headroom` 组合报告
\(D_N,D_C(\alpha),D_B(\alpha),D_J(\alpha)\)，形成九条四点离散需求曲线。
目标之间不插值，也不把四个点描述成连续边界。

当前包络含事件启动、最小事件功率、持续时间和恢复约束，所以
\(D(\alpha)\) 的跨目标单调性不作为先验。若出现目标提高但最低柔性下降，必须
同时发布逐时调用、事件分段和 binding-constraint witness，证明该现象来自包络
结构而非实现漂移。

每条曲线还报告：

1. 第一个满足 \(I_{\mathrm{joint}}>10^{-6}\)和
   \(I_{\mathrm{joint}}<-10^{-6}\) 的注册目标；
2. 在归一化柔性上限 1 内可交付的最高注册目标；
3. 每个目标的 resolved、training-support failure、cap-infeasible 或 unresolved
   状态。

## 5. 确认性参数设计

主设计采用完整 \(4\times3\times3\) factorial：

- `hourly_cfe_target`：0.50、0.70、0.85、1.00；
- `flexible_fraction`：0.05、0.20、0.50；
- `normalized_recovery_headroom`：0.00、0.10、0.30。

共 36 个 primary cells。其余参数固定在：

- `recovery_efficiency=0.85`；
- `maximum_event_duration_hours=4`；
- `maximum_event_count=2`；
- `normalized_energy_budget=0.40`；
- `normalized_debt_limit=0.20`。

在 \(\alpha=0.85\)、`flexible_fraction=0.20`、
`normalized_recovery_headroom=0.10` 的锚点上，对上述五个时序参数分别使用原有
三档做 OAT，每个参数新增两个非基准 cell，共新增 10 个 cells。确认性设计总计
46 个唯一 cells。所有 cells 必须发布，不按结果删减。

这组水平完全继承既有冻结设计中的数值，不依据未来 successor 结果移动阈值。
70-cell结果只作为提出本问题的探索性前序；该 successor 是对尚未执行的完整
public-block协议进行前瞻性确认，不构成外部样本复制。

## 6. 训练与 holdout

代表点只使用 training blocks，并按 \(\alpha=1\) 的冻结压力分数一次选定；全部
46 cells 使用相同的 8 个电力代表块和 8 个业务代表块。代表点上的最小容量只是
候选值，必须在完整可评估 training Cartesian support 上复核。

通过复核后冻结容量：

- correct joint policy 使用 \(D_J\)；
- B6 policy 使用 \(D_B\)；
- holdout 不重新选择容量；
- holdout 只使用当前可见状态，按 grid-first 规则执行；
- 两项联合策略均在真实共享包络中执行。

主要运行后果为：

- joint service failure probability；
- hard-grid failure probability；
- CFE service failure probability；
- expected total service shortfall；
- expected CFE shortfall。

主要对比是 B6 减 correct。peak/terminal recovery debt 单列描述；只有未来
注册并实现明确 violation 字段后，债务才可进入失败判定。

## 7. 归因规则

结果使用可并存的 bottleneck vector，不强制每个 cell 进入一个互斥区域：

1. `network_single_service_binding`：网络单服务被证明不可行，或其注册风险为
   all-coupling robust positive；
2. `cfe_single_service_binding`：CFE单服务满足同样条件；
3. `joint_extra_requirement`：\(I_{\mathrm{joint}}>10^{-6}\)；
4. `joint_portfolio_relief`：\(I_{\mathrm{joint}}<-10^{-6}\)；
5. `b6_capacity_underprovisioning`：\(A_{\mathrm{B6}}>10^{-6}\)；
6. `b6_capacity_overprovisioning`：\(A_{\mathrm{B6}}<-10^{-6}\)；
7. `b6_operational_penalty`：至少一项 B6-minus-correct 服务风险的 transport
   lower bound 大于 \(10^{-6}\)。

“联合后才不足”要求两个单服务 arm 均已解析且不构成瓶颈，同时 joint-correct
被证明在注册上限不可行，或 \(I_{\mathrm{joint}}>10^{-6}\)。

## 8. 不确定性与证据边界

训练端的容量前沿使用完整 Cartesian support 审计，不以某个假设配对概率定义。
holdout 服务风险在 finite-grid blocks 与 workload blocks 的完整 transport
polytope 上计算 sharp bounds。多指标陈述必须由同一个 coupling witness 支持。
E0质量无条件单列，不进入条件服务风险。

固定 seed `20260825`、200次 independent marginal block bootstrap 只描述经验边缘
抽样变化。项目结论限于注册公开 benchmark，不外推为现实合同发生率、总体违约
概率、条件容量 \(X\)、绝对 Alibaba MW 或工程安全认证。

## 9. 完成与停止条件

以下任一情况使相应结论保持未决：

- 四臂任一必要证书缺失；
- 46-cell inventory不完整；
- 完整training-support审计失败；
- 分解恒等式失败；
- holdout Cartesian pair、E0行或transport证书不完整；
- 多指标结论没有共同 coupling witness。

正式结果无论是否出现正或负的 \(I_{\mathrm{joint}}\)、\(A_{\mathrm{B6}}\) 或运行风险，
均完整发布。结果不触发同一协议内的目标、参数、阈值或样本调整。
