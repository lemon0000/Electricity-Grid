# RQ2 联合服务可交付前沿与归因指标 v2

> 状态：`SEALED_READY_FOR_INDEPENDENT_REVIEW`。本文件与
> `configs/rq2_joint_deliverability_preregistration_successor_v3.yaml`
> 共同修复首次独立R4提出的5项Major。旧v1/v2字节保持不变。本文件不授权solver、
> formal run、结果发布或论文claim。

## 1. 研究对象

研究对象仍是：在网络安全调用保持为硬服务时，提高小时级CFE目标如何改变联合
服务所需的最低业务柔性，并区分单服务瓶颈、联合时序交互和B6分离记账偏差。

所有容量均以 \(D_{DC}=1\) 归一化。每个样本是24小时、1小时时间步、初始恢复
债务为0且初始事件未激活的完整block。期末要求事件停止且恢复债务为0。

## 2. CFE请求与恢复资格

由 \(\alpha=1\) 的原始CFE调用比例重建可再生份额：

\[
s^{RE}_{it}=1-d^{CFE,1}_{it},\qquad 0\le s^{RE}_{it}\le1.
\]

目标 \(\alpha\in\{0.50,0.70,0.85,1.00\}\) 下的完整CFE请求为

\[
c_{it}(\alpha)=\frac{\max\{\alpha-s^{RE}_{it},0\}}{\alpha}.
\]

该请求不按当前业务可用柔性截断。业务恢复余量和CFE兼容恢复余量分别为

\[
\bar r^{business}_{jt}
=h\max\{1-o_{jt},0\},
\]

\[
\bar r^{CFE}_{it}(\alpha)
=\max\left\{\frac{s^{RE}_{it}}{\alpha}-1,0\right\},
\]

其中 \(o_{jt}=\min\{\text{raw workload fraction},1\}\)，\(h\) 是注册的
`normalized_recovery_headroom`。承担CFE义务的轨迹使用

\[
\bar r^{joint}_{ijt}(\alpha)
=\min\{\bar r^{business}_{jt},\bar r^{CFE}_{it}(\alpha)\}.
\]

恢复只允许在对应时序track未激活的小时发生。

## 3. 四臂及恢复语义

| 容量 | 规划调用 | 规划恢复 | 执行恢复 |
|---|---|---|---|
| \(D_N\) | 仅网络，共享track | 仅业务恢复余量 | 仅业务恢复余量 |
| \(D_C\) | 仅CFE，共享track | CFE兼容恢复余量 | CFE兼容恢复余量 |
| \(D_J\) | 网络+CFE，共享track | CFE兼容恢复余量 | CFE兼容恢复余量 |
| \(D_B\) | 网络、CFE分离track | 网络track用业务余量；CFE track用CFE兼容余量 | 两项服务回到共享track，使用CFE兼容余量 |

B6规划仍对两项服务分别使用完整`available_flexibility`，但保留共享
`connected_demand`上限；两个track分别维护事件、累计能量和恢复债务。B6
holdout不得沿用两套恢复状态，而必须在真实共享状态中以冻结的 \(D_B\) 执行。

该定义保证 \(D_N\) 是纯网络单服务基线。对相同的非\(\alpha\)参数和training
support，四个目标必须引用同一份 \(D_N\) 输入hash和容量证书；不重复求解，也不
允许因 \(\alpha\) 改变网络基线。

## 4. 完整时序包络

除46-cell中显式变化的参数外，以下值固定：

| 字段 | 值 |
|---|---:|
| `maximum_flexibility_budget` | 1.0 |
| `minimum_recovery_hours` | 1.0 |
| `minimum_event_power` | \(10^{-6}\) |
| `response_time_hours` | 1.0 |
| `curtailment_ramp_per_hour` | 1.0 |
| `service_shortfall_tolerance` | \(10^{-6}\) |
| `terminal_recovery_debt_limit` | 0.0 |

基准时序参数仍为：

- `recovery_efficiency=0.85`；
- `maximum_event_duration_hours=4`；
- `maximum_event_count=2`；
- `normalized_energy_budget=0.40`；
- `normalized_debt_limit=0.20`。

业务可用柔性为

\[
a_{jt}=f\,o_{jt},
\]

其中 \(f\in\{0.05,0.20,0.50\}\)。共享track满足
\(g_t+c_t\le a_{jt}\)；B6规划中的每个分离track分别满足不超过 \(a_{jt}\)，并
共同满足连接需求上限。

## 5. 46-cell与代表点

主设计保持 \(4\times3\times3=36\) 个cells。OAT锚点为
\(\alpha=0.85,f=0.20,h=0.10\)，对5个时序参数各加入2个非基准水平，共10个
cells。总数必须恰好为46，cell tuple和cell ID均不得重复。

代表点算法唯一规定如下：

1. 只使用training split；power侧先排除E0，再重新归一化有限状态概率。
2. power score为 \(\alpha=1\) 下
   \(\max_t\{g_{it}+c_{it}(1)\}\)；workload score为
   \(\max_t o_{jt}\)。
3. 按`(score, ASCII block_id)`升序排列。
4. 对 \(q_k=(k+0.5)/8,\ k=0,\ldots,7\)，选择累计概率首次达到 \(q_k\) 的block。
5. 重复ID保留第一次，再按排序结果补足至8个唯一ID。
6. 每个原始block分配给score距离最近的代表；距离相同时选择ASCII ID较小者。
7. 代表概率等于分配给它的原始概率之和。
8. power和workload代表ID只选择一次，并供全部46 cells共同使用。

代表点容量只是候选。完整可评估training Cartesian support中任一pair失败时，
相应estimand记为`training_support_failure_estimand_undefined`，不得增加容量或
重选代表点。

## 6. 容量证书与有符号归因

每个已解析arm必须提供目标下界 \(L_a\) 和已审计可行incumbent上界 \(U_a\)：

\[
D_a\in[L_a,U_a].
\]

`minimum_capacity`记录 \(U_a\)，不能脱离证书单独使用。四个arm均已解析且通过
完整training support后，点估计仍定义为

\[
D_{\text{single}}=\max(D_N,D_C),
\]

\[
I_{\text{joint}}=D_J-D_{\text{single}},
\quad
I_{\text{sep}}=D_B-D_{\text{single}},
\quad
A_{\text{B6}}=D_J-D_B.
\]

点估计必须满足

\[
I_{\text{joint}}=I_{\text{sep}}+A_{\text{B6}}
\]

且残差不超过 \(10^{-6}\)。符号判断使用完整证书区间：

\[
D_{\text{single}}\in
[\max(L_N,L_C),\max(U_N,U_C)],
\]

\[
I_{\text{joint}}\in
[L_J-\max(U_N,U_C),\ U_J-\max(L_N,L_C)],
\]

\[
I_{\text{sep}}\in
[L_B-\max(U_N,U_C),\ U_B-\max(L_N,L_C)],
\]

\[
A_{\text{B6}}\in[L_J-U_B,\ U_J-L_B].
\]

对任一contrast区间 \([\ell,u]\)：

- `robust_positive`：\(\ell>10^{-6}\)；
- `robust_negative`：\(u<-10^{-6}\)；
- `certified_near_zero`：\([\ell,u]\subseteq[-10^{-6},10^{-6}]\)；
- 其余为`numerically_indeterminate`。

不得用incumbent点值越过证书区间。timeout、缺incumbent、缺bound、gap或残差
证书失败均记为`unresolved`，不得解释为不可行。

## 7. alpha=1结构性端点

由于 \(s^{RE}\le1\)，在 \(\alpha=1\) 时
\(\bar r^{CFE}_{it}(1)=0\)。若某个planning track同时满足：

1. 24小时恢复上界全部为0；
2. 必需调用总能量大于0；
3. 初始恢复债务为0；
4. 期末恢复债务上限为0；

则由债务平衡式可直接证明该track对任意容量均不可恢复。此时不调用solver，
而记录：

`structural_recovery_infeasible_estimand_undefined`。

witness必须包含arm、track、调用总能量、最大恢复余量、初始/期末债务以及债务
恒等式。该点仍保留在注册网格中，用于标记accounting boundary，但不是数值容量
点。四臂任一estimand未定义时，不计算 \(I_{\text{joint}},I_{\text{sep}},A_{\text{B6}}\)，
不得声称联合交互或B6偏差的方向。

## 8. 固定策略holdout

只有四臂容量均已解析且training support全部通过的cell进入holdout。容量、代表点
和策略不得重选。

每小时策略只读取当前状态，并按字典序执行：

1. 在当前共享包络可行集中最大化网络服务；
2. 用剩余可行集合最大化CFE服务；
3. 当总调用为0时，在注册恢复上界内最大化恢复。

当前可行集必须包含容量、业务可用量、连接需求、ramp、最小事件功率、持续时间、
事件次数、休息时间、累计能量、恢复债务和对应arm的恢复上界。不得读取未来调用
或未来状态。

定义

\[
S^N=\sum_t\max(g_t-\hat g_t,0)\Delta t,
\qquad
S^C=\sum_t\max(c_t-\hat c_t,0)\Delta t,
\]

\[
S^{total}=S^N+S^C.
\]

`hard_grid_failure`为 \(S^N>10^{-6}\)，`cfe_service_failure`为
\(S^C>10^{-6}\)。对完整block，期末恢复债务大于 \(10^{-6}\) 记为
`recovery_completion_failure`。`joint_service_failure`为三者任一成立。
峰值和期末债务数值继续单列描述；不完整或right-censored block的这些服务指标
全部未定义，而非当作成功。

主要运行对比仍为B6减correct：

- joint service failure probability；
- expected total service shortfall；
- expected CFE shortfall。

## 9. E0、transport与bootstrap

E0无条件质量定义为

\[
m_{E0}=\sum_i p_i\,1\{state_i=E0\}.
\]

该质量只报告一次。E0行不生成服务指标，不进入有限状态服务风险的分子或分母。
有限power边缘按

\[
p_i^F=\frac{p_i}{1-m_{E0}}
\]

重新归一化，workload边缘保持不变。transport ambiguity set是这两个有限离散
边缘上的完整transport polytope。

每个标量端点均需primal、dual和attaining witness。包含多个指标符号的陈述必须
由同一个coupling \(\pi\) 支持。

bootstrap固定为200次、seed `20260825`。每次分别从530个power holdout IDs和
34个workload holdout IDs的注册经验边缘有放回抽样；重复ID折叠为频数权重，E0
状态随power ID保留，随后重新计算有限条件边缘和全部transport端点。任一replicate
没有有限power support时，bootstrap区间整体记为`unresolved`；否则报告2.5%和
97.5%等尾percentile。

## 10. 结论边界

结果仅适用于注册公开benchmark。结构性端点不能外推为现实容量不足；transport
区间不能解释为已观测联合分布；bootstrap不能修复跨源不可配对。任何结果均不
构成现实合同发生率、总体违约概率、绝对Alibaba MW、full-N-1、AC安全或工程认证。
