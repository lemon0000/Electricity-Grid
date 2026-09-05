# RQ2 联合服务可交付前沿与归因指标 v3

> 状态：`SEALED_READY_FOR_INDEPENDENT_REVIEW`。机器协议见
> `configs/rq2_joint_deliverability_preregistration_successor_v4.yaml`。
> 本文件不授权implementation、solver、formal run、结果发布或论文claim。

## 1. 研究问题与证据范围

在网络安全调用保持为硬服务时，研究小时级CFE目标
\(\alpha\in\{0.50,0.70,0.85,1.00\}\)如何改变联合服务所需的最低业务柔性，
并区分单服务瓶颈、联合时序交互和B6分离时序记账偏差。

结论对象是公开数据构成的24小时归一化benchmark，不是现实合同发生率、经验联合
分布、总体违约概率、绝对Alibaba MW、条件容量X、full-N-1、AC安全或工程认证。

v4机器协议是完整、自包含的候选权威。达到seal commitment point后，本版本才成为
独立R4的审查对象；历史版本只记录来源与审查链，不通过字段遗漏补充当前语义。

## 2. 数据与归一化

power边缘使用541个training blocks和530个holdout blocks；workload边缘分别为
34和34个blocks。每个block为24小时、\(\Delta t=1\)小时。

power小时文件固定为`dispatched_power_system_blocks.csv.gz`，逻辑字段映射为：

- `cfe_call_fraction_at_alpha_1 ← cfe_call_fraction`；
- `grid_need ← grid_need_fraction`；
- `hourly_grid_state ← dispatch_state`。

workload小时文件固定为`workload_blocks.csv.gz`，
`raw_workload_fraction ← workload_fraction`。两侧marginal文件均为
`training_marginal.csv.gz`或`holdout_marginal.csv.gz`，列严格等于
`id,probability`。小时行按`block_id,hour_offset`唯一，offset必须为0至23。

只要power block内任一小时为`exogenous_grid_infeasibility`，整个block提升为E0；
否则24小时必须全部为`finite_grid_need`。未知或未决状态使输入包失效。

容量以 \(D_{DC}=1\) 归一化，短缺以 \(D_{DC}\cdot h\) 计量。每个block从零恢复
债务和非激活事件开始，只有一个完整period，期末要求事件停止且恢复债务为0。

## 3. CFE调用与恢复

由 \(\alpha=1\) 的调用比例重建可再生份额：

\[
s^{RE}_{it}=1-d^{CFE,1}_{it},\qquad 0\le s^{RE}_{it}\le1.
\]

目标 \(\alpha\) 下的完整CFE调用为

\[
c_{it}(\alpha)=\frac{\max\{\alpha-s^{RE}_{it},0\}}{\alpha}.
\]

该调用不截断到业务可用柔性。为使binary event语义与数值容差一致，network和
CFE原始请求若不超过\(10^{-6}\)则将有效请求记为0，否则有效请求等于原始请求；
原始请求仍保留用于审计。以下规划、结构门、holdout服务和shortfall均使用有效
请求。令workload occupancy为
\(o_{jt}=\min\{\text{raw workload fraction},1\}\)，则

\[
a_{jt}=f o_{jt},
\]

\[
\bar r^{business}_{jt}=h\max\{1-o_{jt},0\},
\]

\[
\bar r^{CFE}_{ijt}(\alpha)=
\min\left\{\bar r^{business}_{jt},
\max\left(\frac{s^{RE}_{it}}{\alpha}-1,0\right)\right\}.
\]

恢复只在对应track未激活时发生。

## 4. 四臂

| 符号 | arm | 规划恢复语义 | 执行语义 |
|---|---|---|---|
| \(D_N\) | `network_only_shared` | shared track只用业务恢复余量 | shared、业务恢复 |
| \(D_C\) | `cfe_only_shared` | shared track用CFE兼容恢复余量 | shared、CFE兼容恢复 |
| \(D_J\) | `joint_correct_shared` | 网络与CFE共用track及CFE兼容恢复余量 | shared、CFE兼容恢复 |
| \(D_B\) | `joint_b6_separate_planning_shared_execution` | grid track用业务恢复；CFE track用CFE兼容恢复 | 两项服务回到shared track及CFE兼容恢复 |

B6规划中的两个track分别维护事件、能量和恢复债务，各自可使用完整业务柔性，
但共同受连接需求上限约束。B6不是纯瞬时容量重复的单因素处理，而是分离时序状态
和恢复资格的整体诊断基线。

\(D_N\) 的canonical key排除\(\alpha\)。非\(\alpha\)参数和support相同的四个目标
必须引用相同输入hash和容量证书，不重复求解。

### 4.1 规划方程

对scenario \(s\)、hour \(t\)和arm对应track \(k\)，变量为容量 \(D\)、网络服务
\(x^N_{st}\)、CFE服务 \(x^C_{st}\)、track调用 \(q_{skt}\)、活动状态
\(z_{skt}\)、启动/停止 \(u_{skt},v_{skt}\)、恢复 \(r_{skt}\)和债务
\(b_{skt}\)。目标为\(\min D\)。

网络arm满足 \(x^N_{st}\ge \tilde g_{st}\)，无网络服务的arm令 \(x^N_{st}=0\)；
CFE arm满足 \(x^C_{st}=\tilde c_{st}(\alpha)\)，无CFE服务的arm令
\(x^C_{st}=0\)。CFE不得超额服务；网络允许为满足最小事件功率而超额削减。

shared track定义 \(q=x^N+x^C\)；B6定义
\(q^{grid}=x^N,q^{cfe}=x^C\)。所有arm满足

\[
x^N+x^C\le1,\qquad 0\le q_{skt}\le D\le1.
\]

shared arm还满足 \(x^N+x^C\le a_{st}\)；B6则分别满足
\(x^N\le a_{st},x^C\le a_{st}\)。连接需求上限只约束削减调用，不约束恢复或
净负荷；恢复由独立rebound headroom约束。

活动、ramp和债务约束为：

\[
q_{skt}\le z_{skt},\qquad
q_{skt}\ge q^{min}z_{skt},
\]

\[
q_{skt}-q_{sk,t-1}\le
\min\{\rho\Delta t,\rho\tau^{resp}\},
\]

\[
0\le r_{skt}\le
\min\{\bar r,\bar r_{skt}^{track}\}(1-z_{skt}),
\]

\[
b_{skt}=b_{sk,t-1}+q_{skt}\Delta t
-\eta r_{skt}\Delta t,\qquad 0\le b_{skt}\le\bar b.
\]

初始 \(q=z=b=0\)。标准三条binary约束精确定义start和stop。任意
\(W+1\)小时窗口的活动和不超过 \(W\)，每次stop后的 \(R\) 个索引不得重新启动，
全block启动数和调用能量分别不超过注册上限。hour 23满足
\(z_{sk,23}=0,b_{sk,23}=0\)。

B6两个track可出现一条track恢复、另一条track调用；这是分离时序记账反事实。
每条track独立应用恢复、事件、能量和债务约束，恢复不进入共享连接需求上限。

## 5. 时序包络与46-cell设计

固定参数如下：

| 参数 | 值 |
|---|---:|
| 最大归一化容量 | 1.0 |
| 最小恢复间隔 | 1小时 |
| 最小事件功率 | \(10^{-6}\) |
| 响应时间 | 1小时 |
| ramp | 1.0/小时 |
| 服务短缺容差 | \(10^{-6}\) |

主设计是
\[
4\ \alpha\times3\ f\times3\ h=36
\]
个cells。在\(\alpha=0.85,f=0.20,h=0.10\)锚点上，分别改变
`recovery_efficiency`、`maximum_event_duration_hours`、
`maximum_event_count`、`normalized_energy_budget`和
`normalized_debt_limit`，每项加入2个非基准水平，共10个OAT cells。总计46个
唯一参数tuple和唯一cell ID，全部报告。

## 6. 代表点与完整training支持

代表点只由training数据决定。power侧先排除E0并重新归一化。power score为
\(\max_t\{g_{it}+c_{it}(1)\}\)，workload score为\(\max_t o_{jt}\)。

两侧分别按`(score, unsigned UTF-8 block-ID bytes)`升序排列，并在
\[
q=(0.0625,0.1875,\ldots,0.9375)
\]
选择累计概率首次达到目标的block。重复ID保留第一次，再按原排序补足8个唯一ID。
每个源block分配给score距离最近的代表；距离相同时取UTF-8字节序较小者。代表
概率为被分配源概率之和。两侧代表ID只选一次，供全部46 cells使用。

代表点解只是候选。候选必须通过完整可评估training Cartesian support；失败后
不得增加容量或重选代表点。

## 7. 全局零恢复结构门

在任何容量solver调用前，对

\[
\text{arm}\times\text{track}\times\text{cell}\times
\text{full evaluable training pair}
\]

执行解析检查。先按第3节把原始必需调用映射为有效调用
\(\tilde q_t^{req}\)。只有\(\tilde q_t^{req}=0\)的小时是可恢复小时：

\[
r_t^{eligible}=
\begin{cases}
\min\{\bar r,\bar r_t^{track}\}, & \tilde q_t^{req}=0,\\
0, & \text{otherwise}.
\end{cases}
\]

债务的解析下界为

\[
\underline b_T=b_0+\sum_t\tilde q_t^{req}\Delta t
-\eta\sum_tr_t^{eligible}\Delta t.
\]

若 \(\underline b_T>\bar b_T+10^{-12}\)，则该arm-cell记为
`structural_recovery_infeasible_estimand_undefined`，保存精确pair、track和债务
恒等式witness，不调用solver、不填补数值容量、不进入holdout，也不计算任何需要
四臂完整的容量contrast。

\(\alpha=1\)导致CFE兼容恢复恒为0，只是该通用规则的一条充分触发路径。
`normalized_recovery_headroom=0`等其他零恢复情形执行同一检查。

## 8. 容量证书、前沿与归因

每个resolved arm必须给出

\[
D_a\in[L_a,U_a],
\]

其中 \(L_a\) 是有效solver objective lower bound，\(U_a\) 是通过数值审计和完整
training support的feasible incumbent。报告点值为 \(U_a\)，但分类只能使用区间。

\[
D_{\text{single}}\in
[\max(L_N,L_C),\max(U_N,U_C)],
\]

\[
I_{\text{joint}}\in
[L_J-\max(U_N,U_C),U_J-\max(L_N,L_C)],
\]

\[
I_{\text{sep}}\in
[L_B-\max(U_N,U_C),U_B-\max(L_N,L_C)],
\]

\[
A_{\text{B6}}\in[L_J-U_B,U_J-L_B].
\]

点值还必须满足

\[
I_{\text{joint}}=I_{\text{sep}}+A_{\text{B6}}
\]

且残差不超过 \(10^{-6}\)。

区间下界大于 \(10^{-6}\) 才是`robust_positive`；区间上界小于
\(-10^{-6}\) 才是`robust_negative`；完整区间落在
\([-10^{-6},10^{-6}]\)内才是`certified_near_zero`；其余为
`numerically_indeterminate`。

离散前沿只在四臂均resolved时形成数值点。首次正负交互目标、全部capacity labels
和paper claim均使用上述区间规则；不使用点值越过证书。结构性、support failure、
cap-infeasible和unresolved状态保留，但不伪造成数值点。

归因输出为可并存vector：

- network/CFE single-service binding；
- joint extra requirement、portfolio relief、near-zero或indeterminate；
- B6 capacity underprovisioning、overprovisioning、near-zero或indeterminate；
- B6 operational penalty或relief。

status-based单服务标签不要求其他arm resolved。任一arm为structural或
cap-infeasible时，可以报告对应单服务瓶颈，但全部signed capacity labels为
`not_evaluable`。signed labels仅在四臂均resolved时求值；operational labels还要求
holdout、transport和common-\(\pi\)证书完整。某一arm为unresolved或training-support
failure时，只令该arm的status label不可评价，不抹去其他arm已经取得的structural或
cap-infeasible标签。四臂resolved但holdout/transport未解析时，基于service-risk的
single-service label仍为`not_evaluable`。

## 9. 固定策略holdout

只有四臂均resolved且training support通过的cell进入holdout。每小时策略只读取
当前请求、当前可用量及上一小时结束后的状态。初始`previous_call=0`、inactive，
duration/count/energy/debt均为0，rest为null且`has_prior_event=false`：

1. 在当前共享可行行动集中最大化grid served；
2. 固定grid served后最大化CFE served；
3. inactive时最大化允许恢复；
4. 依次更新事件、能量、休息和恢复债务。

行动变量满足 \(0\le\hat g_t\le\tilde g_t\)、
\(0\le\hat c_t\le\tilde c_t\)，
\(q_t=\hat g_t+\hat c_t\)。调用上限为冻结容量、当前业务可用量和连接需求的最小值。
inactive严格要求 \(q_t=0\)；active要求 \(q_t\ge q^{min}\)。只限制向上ramp。
start、duration、rest、event count和累计能量按第4节同一离散语义更新。

调用后债务为 \(b_t^-=b_{t-1}+q_t\Delta t\)。活动时恢复为0；非活动时第三个
词典序目标唯一确定

\[
r_t=\min\left\{\bar r,\bar r_t^{current},
\frac{b_t^-}{\eta\Delta t}\right\},
\qquad b_t=b_t^--\eta r_t\Delta t.
\]

hour 23强制inactive并最大化当前允许恢复；\(b_{23}>0\)时记录recovery
completion failure，而不是令当前行动集为空或使用未来请求重优化。

定义grid和CFE短缺能量为

\[
S^N=\sum_t\max(g_t-\hat g_t,0)\Delta t,\qquad
S^C=\sum_t\max(c_t-\hat c_t,0)\Delta t.
\]

`joint_service_failure`等于grid短缺、CFE短缺或完整block期末恢复债务超过
\(10^{-6}\)中的任一项。B6和correct均在共享物理状态中执行，容量分别固定为
\(D_B\)和\(D_J\)。不完整或right-censored block的服务指标为undefined。

## 10. E0、transport与bootstrap

E0质量按唯一power block ID计算：

\[
m_{E0}=\sum_{\text{unique }i}p_i1\{state_i=E0\}.
\]

无条件报告一次。E0不生成pairwise服务指标，也不进入有限服务风险分子或分母。
finite power权重按 \(p_i/(1-m_{E0})\)重新归一化，与完整workload holdout边缘形成
transport polytope。rows和columns均按unsigned UTF-8 ID字节序排列，
\(\pi_{ij}\)按row-major展开。等式矩阵依次写全部row sums及除最后一列外的column
sums。lower最小化metric，upper最小化其相反数。

若 \(m_{E0}\ge1-10^{-9}\)，则有限支持为空：E0质量仍无条件报告，但finite service
metrics、transport和common-\(\pi\)统一记为
`finite_service_identification_unresolved`，且不得调用transport solver或执行除零。

transport固定Python 3.11.15、NumPy 1.26.4、SciPy 1.17.0及SciPy bundled
HiGHS 1.8.0，使用`linprog(method="highs-ds")`、presolve和\(10^{-9}\) primal/
dual tolerance，`OMP_NUM_THREADS=1`。每个标量端点需要primal、free equality
dual、attaining coupling、至多\(10^{-8}\)的对偶间隙和边缘残差。

common-\(\pi\)只评价两个注册operational labels。每个label分别对
`B6_minus_correct_joint_service_failure`、
`B6_minus_correct_total_service_shortfall`和
`B6_minus_correct_cfe_shortfall`建立三个单谓词分支；penalty使用
`robust_positive`，relief使用`robust_negative`，任一分支compatible即支持对应
“at least one”标签。每个分支求解单一shared-slack phase-I LP。具有有效primal
witness且最优slack不超过\(10^{-8}\)才为compatible；只有有效dual feasible
lower bound严格大于\(10^{-8}\)才为certified incompatible，其余均为unresolved。
证书同时要求primal-dual gap、边缘残差和谓词残差不超过\(10^{-8}\)。证书float权威表示为
IEEE-754 `float.hex()`，JSON采用sort-keys、compact separators、UTF-8和末尾换行。

bootstrap固定为Python 3.11.15、NumPy 1.26.4、
`Generator(PCG64DXSM(20260825))`。power和workload IDs按unsigned UTF-8字节序排列，
概率转为float64并除以`math.fsum`。同一个generator按replicate 0至199依次消费：
先按原power概率有放回抽530次，再按原workload概率有放回抽34次；重复ID折叠为
频数除以抽样数。

每次重新计算E0质量、finite conditioning和transport endpoints。CI使用
`numpy.quantile(q=[0.025,0.975], axis=0, method="linear")`。只要任一replicate
没有finite power mass，所有cell、metric和endpoint的bootstrap结果统一记为
`unresolved`。
