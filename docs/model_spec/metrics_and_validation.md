# 指标、基线与验证门槛

## 1. 指标计算原则

- 指标从保存的原始规划和逐时运行表计算，不直接从求解器日志手工抄录。
- 所有方法在相同训练场景、场景外路径、安全集合、CFE目标和成本口径下比较。
- 规划指标按长期路径计算后报告概率加权均值、分位数和最坏值；不能只报告期望。
- 物理指标和货币指标分开保存，避免成本系数掩盖服务或安全差异。

## 2. 容量里程碑

对比例 $p\in\{0.2,0.5,1.0\}$，定义有运营意义的门槛

$$
R_p=\max\{pP^{app},B_{min}\}.
$$

对长期路径 $\omega$，只有当节点 $n_k(\omega)$ 满足以下条件时，容量里程碑才算形成：

1. $C_{n_k(\omega)}\ge R_p$；
2. 正常状态可交付完整 $C$；
3. 所有规定关键N-1状态至少可交付F，且X调用不超过合同包络；
4. 上述条件在一个长度不少于 $H_{min}$ 的连续验证窗口内成立；
5. 工程容量只使用已经实际投运的 $v=1$ 项目。

于是

$$
T_p(\omega)=\min\{k:\text{上述五项在 }n_k(\omega)\text{成立}\}.
$$

分别记为 $T20,T50,T100$。若规划期内未达到，记为右删失值 `K+`，汇总时同时报告未达标概率，不能简单把它替换成最后一个季度。

首个可运营模块为

$$
T_{module}(\omega)=\min\{k:C_{n_k(\omega)}\ge B_{min}\text{ 且通过连续可交付性校核}\}.
$$

因此1 MW或任意数值噪声不能触发“首次送电”。

当前M3固定策略的静态DC状态门不再把“重复静态条件”计作连续验证，配置中的连续验证小时为0；其scope为`released_capacity_threshold_in_static_dc_state_set_with_declared_window_assumption`，所有正式T均保持右删失。独立连续包络使用RTS-GMLC 2020的8784个连续时间戳和一条显式合成调用轨迹，scope为`released_capacity_model_validated_over_explicit_chronological_sensitivity_trace`。该轨迹得到`T_module=T20=q1,T50=q3,T100=q4+`，只证明给定恢复模型下的机制边界，不是逐时网络安全或合同认证。

原生RTS-GMLC 6小时和完整day-0 24小时benchmark都不能用于确认T指标：二者的业务柔性、可恢复量和恢复headroom均为0，且`completed_periods=[]`。逐时电网耦合成立不等于连续业务容量里程碑成立。

## 3. 服务与业务指标

对正常运行状态，定义：

$$
E^{access}=\sum\omega_w\Delta t\,u^{access},
$$

$$
E^{grid}=\sum\omega_w\Delta t\,c^{grid},
$$

$$
E^{green}=\sum\omega_w\Delta t\,c^{green},
$$

$$
E^{drop}=\sum\omega_w\Delta t\,\ell^{drop},
$$

$$
E^{breach,F}=\sum\omega_w\Delta t\,u^F,
\qquad
E^{breach,X}=\sum\omega_w\Delta t\,u^X.
$$

这些字段必须分别输出。主训练模型中 $E^{breach,F}=E^{breach,X}=0$；场景外执行时解锁它们作为不可履约诊断。

服务损失CVaR同时报告：

- 物理版本：以MWh计的 $E^{access}+E^{drop}+E^{breach,F}+E^{breach,X}$；
- 经济版本：按预注册损失系数计算的 $L_\omega$。

不得用经济CVaR代替物理服务缺口表。

## 4. 多阶段适应性价值

令 $\Pi^{B3}$ 和 $\Pi^{B4}$ 分别为两阶段和多阶段得到的固定策略，$\mathcal O$ 为同一组独立场景外路径。标准评估器只重优化小时运行补救，不改变F/X和工程规划规则：

$$
J^{out}(\Pi)=\frac{1}{|\mathcal O|}
\sum_{o\in\mathcal O}J_o(\Pi).
$$

定义

$$
VMA=J^{out}(\Pi^{B3})-J^{out}(\Pi^{B4}).
$$

对最小化问题，$VMA>0$表示多阶段策略更好。还需分别报告：

- $\Delta T20,\Delta T50,\Delta T100$；
- 服务损失均值、P95和CVaR变化；
- 扩建启动与投运季度差异；
- 多阶段策略相对静态B2的改进；
- 完美信息界限 $EVPI=J^{out}(B4)-J^{PI}(B5)$。

B5在同一组场景外路径上逐路径使用完整未来信息重求规划，记为 $J^{PI}$。它不是可执行策略，但理论上应满足 $J^{PI}(B5)\le J^{out}(B4)$；若不满足，说明评估器、可行域或求解精度不一致。

VMA和各项差值使用同一外样本的逐路径配对差，报告配对bootstrap或其他预注册方法得到的置信区间。

当训练目标只识别出端点集合而非唯一政策时，不能任选一个F/X端点计算单点VMA。令可执行端点集合为$\mathcal P^{B3}$和$\mathcal P^{B4}$，先报告

$$
\mathcal V^{out}=\left\{
J^{out}(\Pi^{B3})-J^{out}(\Pi^{B4}):
\Pi^{B3}\in\mathcal P^{B3},\Pi^{B4}\in\mathcal P^{B4}
\right\},
$$

以及其最小/最大值。若各端点结果相同，区间可以退化为单点，但这只说明所选物理指标对已保存端点不敏感，不证明F/X经济拆分唯一。当前M5c使用平衡确定性holdout而非经验随机样本，因此`[110400,110400] MWh`标记为合成holdout适应性值；没有有来源的抽样分布和预注册统计区间时不升级为正式经验VMA。

## 5. unused MW-year

主物理指标度量已释放但基线需求尚未使用的容量：

$$
E^{unused}(\omega)=
\frac{1}{8760}
\sum_{k,w,t}\omega_w\Delta t
\max\{C_{n_k(\omega)}-D^{req}_{k,w,t},0\}.
$$

单位为MW-year。它不把合同削减或绿电移峰误作“达产不足”，也不进入没有容量机会成本的目标函数。

可另报运行净负荷下的POI headroom，但必须使用不同字段名，不能覆盖 $E^{unused}$。

## 6. 重复承诺指标

在同一数据和目标下比较共享预算模型与B6：

$$
\Delta X^{over}_k=X^{B6}_k-X^{shared}_k,
$$

$$
\Delta X^{over,\%}_k=
\frac{X^{B6}_k-X^{shared}_k}
{X^{shared}_k}\times100\%,
\qquad X^{shared}_k>\epsilon^{MW}.
$$

当 $X^{shared}_k\le\epsilon^{MW}$ 时，百分比记为 `NA`，只报告MW绝对高估量；不能用任意小数或 $B_{min}$ 代替分母。

对B6策略在正确物理评估器中的服务请求，定义小时冲突量

$$
o_t=\max\{c^{grid,policy}_t+c^{green,policy}_t-D^{flex}_t,0\}.
$$

冲突能量率和冲突小时率分别为

$$
R^{conflict,E}=
\frac{\sum_t o_t\Delta t}
{\sum_t D^{flex}_t\Delta t},
$$

$$
R^{conflict,H}=
\frac{|\{t:o_t>\epsilon^{MW}\}|}{|\mathcal T|}.
$$

若评估期 $D^{flex}$ 总量为零，冲突能量率记为 `NA`，同时报告绝对冲突能量。

B6场景外执行使用预先固定的分配规则：网络安全调用优先，剩余柔性才用于CFE移峰。被挤出的绿电移峰记为CFE缺口；若即使全部真实柔性用于网络仍不能履约，则记为条件容量服务违约。不得在看到未来路径后重新分配F/X或扩建。

### 6.1 公开边缘v6的容量与E0口径

上式$\Delta X^{over}$只适用于显式求解$X$的模型。公开边缘v6直接求解的是
full-service所需最小业务柔性，故正式容量指标为

$$
\Delta D^{flex}_{min}
=D^{flex,correct}_{min}-D^{flex,B6}_{min}.
$$

该指标无量纲，以$D^{DC}$归一化；机器字段固定为
`flexibility_underprovisioning`。论文不得将其重命名为$X$高估。

对含`exogenous_grid_infeasibility`小时的power block，报告无条件block质量
$p_{E0}$，不生成有限服务、短缺或债务指标。其余合同风险指标均明确标注为
条件量：

$$
\mathbb E_{\pi}[m\mid finite\ grid\ need],
\qquad
\pi\in\Pi(\tilde p,q).
$$

E0不得计入R3。每个报告表同时给出$p_{E0}$和$1-p_{E0}$，防止条件结果被
误读为全样本风险。

逐metric lower/upper endpoint由各自transport LP给出；区域兼容性必须由
同一coupling的联合可行LP验证。200次固定seed的marginal block bootstrap
只给endpoint sampling interval，不能标为population identified set或真实
概率置信区间。

## 7. 履约失败概率

分别定义而不是只给一个合成失败率：

- firm失败：任一小时 $u^F>\epsilon^{MW}$；
- conditional失败：合同调用后仍有 $u^X>\epsilon^{MW}$；
- 包络失败：请求超过MW、持续时间、事件数、累计能量或恢复功率上限；
- 债务失败：$q>Q^{max}$ 或期末债务超过容差；
- CFE失败：年度/小时目标缺口超过容差；
- 联合失败：以上任意一项发生。

场景外概率为

$$
p^{fail}_{out}=\frac{1}{|\mathcal O|}
\sum_{o\in\mathcal O}\mathbf1\{o\text{发生对应失败}\}.
$$

同时使用二项分布置信区间，不只报告点估计。

## 8. 恢复指标

$$
Q^{peak}=\max_t q_t,
$$

$$
R^{peak}=\max_t r^{rec}_t,
$$

$$
E^{terminal}=q_{last+1}.
$$

还需报告最大连续调用时长、事件次数和累计削减能量。若某方案通过MW上限但违反任一时间/能量约束，应判为不可执行，而不是仅增加小额罚值。

## 9. CFE指标

$$
Score^{CFE}=
\frac{\sum_{k,w,t}\omega_w\Delta t\,y^{CFE}_{k,w,t}}
{\sum_{k,w,t}\omega_w\Delta t\,P^{DC}_{k,w,t,0}}.
$$

小时CFE比例定义为

$$
score^{CFE}_t=\frac{y^{CFE}_t}{P^{DC}_{t,0}},
\qquad P^{DC}_{t,0}>\epsilon^{MW}.
$$

零取电小时不进入小时比例分位数，也不能自动记为100%。

同时报告：

- 年度可归属清洁电量和目标缺口；
- 小时CFE Score的P5、P50和P95；
- 未达小时比例；
- 因共享预算而被挤出的绿电移峰能量；
- 年度与小时目标下F/X、扩建和T指标差异。

## 10. 基线的可执行定义

| 基线 | F/X和扩建决策 | 使用的不确定性 | 约束差异 |
|---|---|---|---|
| B0 等待全部扩建 | 永久扩建投运前不释放目标容量；投运后按firm方式接入 | 基准路径 | $X=0$；无提前接入 |
| B1 确定性分阶段 | 在基准达产/工期路径上预先优化季度firm释放和扩建 | 单一基准路径 | $X=0$；允许firm分阶段 |
| B2 静态F/X | 根节点基于基准路径一次预先承诺整个季度F/X与扩建计划 | 单一基准路径 | 后续不得按观测改变计划 |
| B3 两阶段随机 | 根节点基于完整训练分布一次预先承诺整个F/X与扩建计划 | 训练分布已知、实现未知 | 场景后仅小时运行补救 |
| B4 多阶段自适应 | 每个季度节点按已观察历史执行F/X与未开工工程策略 | 同B3 | 节点式规划补救 |
| B5 完美信息 | 每条路径可提前知道全部未来并独立规划 | 完整未来已知 | 不可执行的下界 |
| B6 重复承诺错误模型 | 与选定的正确模型（主实验用B4）完全相同 | 同对应正确模型 | 仅把共享预算拆成两个独立预算 |

B2与B3的区别是是否利用训练分布预先优化；B3与B4的区别是是否能在中间信息揭示后调整规划。所有计划在根节点一次确定，不等于所有容量必须在根节点立即释放。

### 10.1 冻结RTS-24 B0-B2公平机制结果

正式机制比较使用同一输入签名`rts24_b0_b2_common_inputs_v1`。三种政策共享同一条冻结非下降需求路径`50/100/200/250 MW`、季度小时数`2184/2184/2208/2208 h`、系统负荷倍率0.8、bus 8的`50 MW`初始POI和`250 MW`申请上限、两季度工期及同一个branch 11/12热增容捆绑工程。它们也共享排除branch 10后的107态DC安全集合、响应前`RATE_C`、持续态`RATE_A`、同一纠正再调度边界和`75 MW`条件容量上限。工程、服务和成本参数均是冻结合成机制参数；政策之间只改变第10节声明的F/X释放规则，不改变需求、安全集合或求解容差。

主目标先最小化物理接入缺口 $U=\sum_k h_k u_k$，再在同一主最优面报告X暴露集合值。冻结结果为：

| 政策 | $U^*$ (MWh) | X暴露区间 (MWh) | 最小X展示端点，q1-q4的F/X (MW) | 最大X端点，q1-q4的F/X (MW) |
|---|---:|---:|---|---|
| B0 | 327600 | [0, 0] | 0/0，0/0，200/0，250/0 | 同最小X端点 |
| B1 | 109200 | [0, 0] | 50/0，50/0，200/0，250/0 | 同最小X端点 |
| B2 | 109200 | [0, 549600] | 50/0，50/0，200/0，250/0 | 0/50，0/50，125/75，175/75 |

三者都选择q1开工、q3投运。B2与B1的主缺口完全相同，故当前冻结输入下X没有带来额外的物理接入缺口优势；但B2的X暴露区间非退化，说明F/X拆分不可识别。展示采用最小X端点，并继续标记为`conservative_minimum_x_normalization_not_economic_optimum`，不能解释为唯一经济最优。

每种政策均保存10项stage诊断：7个求解阶段为`ok/optimal`，3个集合值或端点审计阶段为`ok/not_applicable`。端点原约束最大违约分别为B0 `9.88e-11`、B1/B2 `8.13e-11`，量级约`1.00e-10`。固定计划进入M3后，每种政策均独立解析actual和contract-counterfactual各428个状态；最大功率平衡残差为B0 `5.74e-11 MW`、B1/B2 `3.05e-11 MW`。

M3主QP后的HiGHS L1线性可行性投影中，最大逐机组移动为B0 `3.35e-7 MW`、B1/B2 `1.96e-7 MW`，均低于`1e-5 MW`门槛；主目标绝对偏差分别为`0.0444`和`0.0368`合成单位，分别低于`5.53`和`5.01`的数值验收包络。这些包络只用于数值验收，是`numerical_feasibility_projection_envelopes_not_optimality_gap_or_error_certificate`，不是最优间隙或误差证书。

由于四个季度的`continuous_validation_hours`均为0，B0-B2的`T_module/T20/T50/T100`一律报告为`q4+`右删失；静态容量值不得替代连续验证。该冻结运行完成M4合成机制门，但所有政策仍保持`security_certified=false`。

### 10.2 原生RTS-GMLC day-0逐时benchmarks

正式归档`rts_gmlc_google_day0_first6h_selected_n1_dc_scuc_v1`和完整日结果`rts_gmlc_google_day0_full24h_selected_n1_dc_scuc_v1`使用RTS-GMLC `v0.2.3`的原生73母线、158条机组记录、120条AC支路和1条DC支路，其中73台常规机组参与组合；它们分别联合Google day-0零柔性派生业务输入的前6个连续小时和完整24小时。两个具名实例均置`chronological_dispatch_request_built=true`和`chronological_grid_dispatch_coupled=true`，但这些标志只关闭各自窗口内的请求构造和原生逐时后端软件门。

该日前selected-N-1 PWL DC-SCUC先以状态约束生成联合优化机组组合，再以固定组合对全部预注册状态执行全状态ED。6小时归档在2轮收敛，全状态ED目标为`157084.446540127 USD`，有效master下界为`157084.446540126 USD`，认证absolute gap为`1e-9 USD`且已报告残差均为0。24小时结果在3轮收敛，全状态ED目标为`1193156.5322057535 USD`，有效active-master下界为`1193155.3829459916 USD`，认证absolute/relative gap为`1.1492597619 USD`/`9.632095e-7`，独立残差最大约`1.4835e-9`。这里的“认证间隙”只针对已声明DC优化问题，不是工程安全认证。

6小时的11个事故状态来自`A27`、`B22`、`C6`、`CB-1`四条关键非孤岛支路和三台关键机组；24小时关键支路改为`A12-1`、`B22`、`C6`、`CA-1`，关键机组仍为`121_NUCLEAR_1`、`213_CC_3`、`313_CC_1`。`B11`和`C11`因会导致孤岛而显式排除。水电和RTPV固定到公开时序，风电/PV可削减；模型只含regional Spin-Up，不含regulation或flex reserve，且CSP、storage和同步调相机禁用有功功率。事故时序CSV为空，因此这些互斥安全状态不是发生过的事故，也不提供事故频次。

两个窗口都保持`completed_periods=[]`；初始开停机和持续时间是自由边界下的优化派生值，不是观测历史。24小时实例已经关闭具名公开benchmark的计算规模门，但二者都不是full N-1、实时SCED或AC安全，继续保持`security_certified=false`和`full_m6_model_input_ready=false`。

RTS-24既有四快照/季度结果与本节两个原生结果使用不同的机组集合和时序口径：前者仍是彼此独立的静态load-only代理，后者才在RTS-GMLC原生资源上链接6或24个小时。原生结果不能回填RTS-24的ramp或机组组合，也不能把RTS-24四快照升级为逐时SCUC；反过来，RTS-24的107态静态结论也不能把本节12态selected-N-1扩大为full N-1。

## 11. 灵活性与绿电变体

| 变体 | 启用约束 |
|---|---|
| F0 无业务灵活性 | $c^{grid}=c^{green}=\ell^{drop}=r^{rec}=0$ |
| F1 MW-only | 仅共享MW上限；不含持续时间、事件、能量和债务 |
| F2 Duration | F1加最大持续时间和事件次数 |
| F3 Full envelope | F2加累计能量、恢复债务、恢复功率和期末边界 |
| G0 无CFE目标 | 不启用年度/小时匹配 |
| G1 年度匹配 | 启用 $\alpha^{ann}$ 年度能量约束 |
| G2 小时级CFE | 启用硬 $\alpha^{hr}$ 逐时约束 |
| G3 高目标压力 | 90%/100%等目标，显式记录最小CFE缺口 |

## 12. 自动测试清单

本节是全项目验收清单，不表示所有条目均已实现。当前自动化已覆盖基础DC-OPF、支路/机组N-1、联合SCOPF、单快照静态机组选择、确定性既有支路热增容、固定策略MW-only F/X服务闭环与里程碑、B0-B2确定性/静态规划机制门、M5a/M5b多阶段随机机制门、M5c固定政策合成holdout、M6a连续灵活性包络、M6b逐时证据输入与调度接口、部分AC恢复、RTS-GMLC数据入口、具名原生6小时及完整24小时selected-N-1日前DC-SCUC/固定组合全状态ED、六候选共同状态多POI结果处理、amendment-004 direct AC、零注入normal对照及560/565/IPOPT诊断runner。full-N1、工程级AC恢复/认证、完整外部证据闭环及CFE条目仍待后续层级实现。

### 12.1 基础电网

1. 数据中心和扩建均为零时，结果复现RTS-24基准DC-OPF。
2. 每个节点、小时和状态的功率平衡残差小于数值容差。
3. 线路容量设为充分大时，不发生网络条件削减。
4. 每个关键N-1故障支路潮流为零，存续支路无热越限。
5. 移除所有可行发电或构造孤岛时模型明确不可行，不通过系统负荷损失恢复可行。
6. 单快照静态机组选择下，停机机组在全部事故状态出力为零；最低负荷107态可行，而需求超过总`Pmax`时仍不可行。

M2微型回归另验证支路短时态逐机组固定正常出力、持续态纠正量不超过上下界，以及故障机组出力严格为零。冻结RTS-24 M2运行对每个状态保存这些审计量，不能只凭“求解最优”推断安全。

原生RTS-GMLC 6小时与24小时benchmark另保存逐小时组合、爬坡、regional Spin-Up、正常态和11个selected-N-1状态审计，并对固定组合全状态ED执行独立残差复算。多POI比较在六候选间统一使用每小时24个共同状态，并把求解可行、LP前缀model-infeasible和计算失败分开处理。该验证只适用于具名日前DC实例，不改变上段RTS-24静态结果，也不满足full N-1、实时或工程AC安全验收。

### 12.2 工程与容量

1. 工程成本极低时，在有需求价值的配置中倾向尽早启动；成本极高时不会无条件建设。
2. 工程在额定工期和实际延期结束前，POI和支路容量增量严格为零。
3. 同一工程沿任一路径最多启动一次，投运后状态不回退；投资成本按启动季度折现。
4. M2既有增容支路自身故障时潮流严格为零，存续并联回路使用投运前/后的正确A/C限额。
5. M2的 $C^{M2}$ 不下降；$F$和 $F+X$单调及等量X转F留到M3验证。
6. M2不改变拓扑或电纳，因此不使用大M；新增候选回路的大M边界仍待后续工程类型实现。

已实现的16项M2机制测试覆盖：零数据中心退化、相同目标优先不启动、严格更小目标不被并列容差隐藏、$K+1$候选与独立求解顺序、原始二次目标避免旧PWL离散选择误差、数值修复包络内/外判定、充分网络不建、低/高工程成本、两季度工期、折现后的延后启动、接入运行需求不回退、原生负荷不足明确不可行、双并联回路N-1，以及支路/机组事故响应。另有OSQP workspace结构变化、不可行证书清空及投影门槛测试。冻结RTS-24合成基准完整解析5个候选，完成4季度×107状态的一次阶段验收。

### 12.3 F/X与服务闭环

1. 逐时验证服务平衡等式，所有组成项可回算到 $P^{DC}$。
2. 当 $D^{req}<F$ 时，实际负荷可较低，但合同容量校核仍必须证明完整F可供。
3. 正常状态合同校核服务完整 $F+X$；关键N-1下服务不低于F。
4. $c^{grid}$从不超过当前活跃X层 $D^X$。
5. 主训练模型 $u^F=u^X=0$；解锁诊断变量后缺口被正确分类。
6. 模型中不存在U容量变量；$u^{access}$不进入网络负荷。
7. X在触发前不削减，并能在 $\tau^{resp}$ 内按 $R^{curt,max}$ 达到所需响应。

M3当前通过第1-6项的固定策略网络机制测试：actual与完整合同反事实网络独立；正常/支路短时态调用为0；持续态actual调用不超过活跃 $D^X$、合同调用不超过X；两层均无firm或调用后conditional违约；低实际需求不绕过完整C校核；F/C单调且X可转F。独立连续包络已经对显式调用轨迹检查第7项的合成响应上界，并补充持续时间、事件数、累计能量、恢复功率和债务边界；它尚未与有真实柔性和事故事件的逐时网络轨迹耦合，参数也不是实测响应证据。原生6小时benchmark虽已耦合零柔性业务请求与selected-N-1安全状态，但事故表为空，不能填补该证据缺口。机组事故仍只有持续态，没有独立响应前频率状态。

### 12.4 信息结构

1. M5a冻结输入必须恰有`6 x 2=12`个需求路径-工程组合，因子概率和叶概率分别归一，叶概率等于对应因子概率乘积。
2. 自然树必须为q1一个根、q2三个当前需求类节点、q3六个`需求类 x 工程状态`节点和q4十二个完整路径节点；节点唯一、父子季度连续、节点叶覆盖和概率递推一致。
3. 六条需求路径共享q1的50 MW，只使用50/100/200/250 MW里程碑，沿路径非下降且不超过250 MW；同一q2需求类仍须保留两个q4终端需求后继，不能在q2泄露完整路径；工程额外工期只能是冻结的0/1季度。
4. B3每季度12叶同一规划决策组；B4组数为`1/3/6/12`；B5每季度均为12个单叶组，角色必须是完美信息界限且`implementable=false`。组内等值只作用于`F/X/z_start`，工程可用状态`v`必须由共享启动决策和各自然历史的Gamma派生。
5. 同一历史节点的F/X和工程启动完全一致；未来信息分叉前决策一致，分叉后才可不同。
6. 单一场景退化时，B3、B4和B5在相同词典序规则下结果一致。
7. 场景标签置换不改变节点决策和目标；工程投运函数Gamma单调，且q3前不能读取工程状态。
8. 同一输入下期望物理缺口满足`U_B5 <= U_B4 <= U_B3`，B5早期场景相关决策必须标记不可执行。
9. M5使用`Dconn=min(Dreq,C)`允许暂未使用的合同权，并继续执行独立合同反事实；不得沿用M4的`C+u_access=Dreq`。
10. 在`U=U*`面先报告总合同容量暴露`E_C`区间；只在minimum-`E_C`面报告X暴露区间，物理端点全部等式锁定后才做非经济工程规范化。
11. M5配置中的公共输入ID、`rts24_common_fair_inputs_v2` schema和SHA-256必须与当前M4配置、RTS-24来源版本及完整107态安全payload重算结果一致；不得只比较固定字符串ID。

### 12.5 灵活性

1. 正确模型逐时满足 $c^{grid}+c^{green}+\ell^{drop}\le D^{flex}$。
2. 合同容量认证满足 $\widehat c^{grid}+c^{green}\le D^{flex,cert}$，不能在认证层重复使用柔性。
3. 构造同时需要网络削减和绿电移峰的小时，B6出现正冲突量而正确模型不出现。
4. 超过 $H^{max}$ 的连续调用不可行。
5. 超过事件次数或最小恢复时间限制的调用不可行。
6. 每1 MWh可恢复削减按 $\eta^{defer}=1$ 进入债务；1 MWh恢复取电只清除 $\eta^{rec}$ MWh债务，且债务不变负。
7. 无链接代表日无法通过债务/持续时间测试；连续周可以正确跨日传递。
8. 窗口边界不能重置事件开关；跨边界长事件仍受持续时间和最小恢复时间约束。
9. 期末债务不能凭空消失。
10. 恢复功率不能使 $P^{DC}$ 超过合同容量或已激活设施物理功率上限。
11. 同一小时不能同时形成新的可恢复削减和执行恢复功率。

### 12.6 CFE

1. $y^{CFE}$不超过同小时数据中心取电、清洁机组出力或可归属上限。
2. 年度匹配只约束加权总能量，小时级匹配逐小时成立。
3. 零清洁出力小时在正小时目标下必须移峰或产生显式缺口。
4. 清洁机组和数据中心同时进入同一网络潮流，不能绕过拥塞。
5. CFE缺口、服务缺口和网络削减输出列彼此独立。

### 12.7 指标与场景外评估

1. 小于 $B_{min}$ 的容量不触发任何T指标。
2. 未在规划期达到的T指标保留右删失标志。
3. VMA的B3/B4使用完全相同的场景外路径和评估器。
4. 场景外评估不能改变既定F/X和工程决策。
5. B6使用固定的网络优先分配规则，并正确记录被挤出的CFE服务。

6. F1/F2/F3消融必须使用完全相同的调用轨迹，只逐层增加时序与恢复约束。
7. 网络minimum-call为零时应报告退化回放，不能用零调用通过证明完整包络可行。
8. F3失败时必须保存逐时债务、季度末债务和导致容量里程碑撤回的季度。

### 12.8 AC事后复核

1. 将代表性DC最优方案的发电、负荷和已投运工程映射到pandapower或PYPOWER AC模型。
2. 正常状态和关键N-1下检查AC潮流收敛、母线电压、线路/主变热限额和无功边界。
3. 若DC可行而AC不可行，不得直接保留该容量；应增加安全裕度、修正候选工程表示或明确解释偏差。
4. 未来主规划至少复核代表性方案，且AC复核不替代主MILP中的全部DC安全约束。当前安全基础另对10%和50%合成响应档位各审计全部107个建模状态。
5. direct replay若发现实现语义错误，父批次必须作废而不能只修汇总标签；修订后必须逐行验证实际slack UID、non-slack PG漂移、完整case覆盖和manifest。

原生RTS-GMLC代表方案amendment-004 direct replay已完成映射和审计，但`0/2304` case满足全部验收条件，因而触发第3项停止规则。amendment-003的`2276/2304`统计和manifest `2b5b705d...`因同址Q-inert机组覆盖唯一Q-capable控制器源`VG`而降为invalidated parent diagnostic，不再作为正式结果：

| POI | PF | case | 收敛 | secure | V违规 | 支路违规 | P违规 | Q违规 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 120 | 1.00 | 576 | 574 | 0 | 574 | 177 | 304 | 571 |
| 120 | 0.95 lagging | 576 | 574 | 0 | 574 | 177 | 304 | 571 |
| 108 | 1.00 | 576 | 575 | 0 | 575 | 179 | 425 | 560 |
| 108 | 0.95 lagging | 576 | 573 | 0 | 573 | 184 | 437 | 515 |

违规类别相互重叠且只统计收敛case。2296个收敛case全部违反电压边界，其中2217个违反Q边界；支路/P违规分别为717/1470。96个normal case全部收敛并全部有V违规，其中93个有Q违规。总体最低/最高电压为`0.650823991/1.125853399 p.u.`，最大电压违规为`0.299176009 p.u.`，最大支路loading为`2.129203046`，最大P/Q违规为`257.547151763 MW`/`287.741739801 Mvar`；DC1最大重构残差为`3e-9 MW`，non-slack PG最大偏差为0。

该结果只能表述为“冻结假设下的无补救direct AC replay完成且安全门失败”。amendment-004 manifest SHA-256为`ee4894bba4e65433ffed4b31e4d96c78035bd2413dd4fa6accb3eb9f16c0609a`。独立零数据中心normal对照24/24收敛但0/24 secure，24个小时均有V/Q违规，支路/P违规分别为11/10；它使用重新优化commitment且不含事故态，不是与treatment逐case匹配的因果对照，但已说明不能把现有违规直接归因于数据中心或POI。没有Q-limit switching、HVDC converter Q、主变/接入线/补偿和工程MVA/控制参数，不能把bus 120称为AC安全站址，也不能把bus 108或其他候选称为工程不可接入。

零注入恢复门按注册顺序给出三层结果：PYPOWER 560的`reference_provider/distributed_committable`为11/24和22/24；统一565 step-control为22/24；独立CasADi 3.7.2/IPOPT的`source/midpoint/flat_target_midq`三组原边界初值各为22/24。后三者均未见证h15/h21；IPOPT的`Infeasible_Problem_Detected`只是一种局部求解器状态，不是全局不可行证明。官方73个母线统一`VMIN/VMAX=0.95/1.05`；对称放宽上下限`0.01 p.u.`后24/24成功但最高`VM=1.06000001 p.u.`，只能作假设敏感性，不能替代正式边界。v2 canonical表以零求解器调用移除v1重复CSV列，科学结果不变；prereg/result manifest分别为`ffdf5d5df29101b463438cbf753e6b80b6babd31d74ea72df82c9648cf236ab3`和`75d40ffe53ded9747f916d57a3d00921d5087549afc8148cb2953f5924bf7332`。

AC-aware commitment v1的真实24小时pre-solver检查因错误的跨小时`BUS_TYPE`静态相等要求而失败；candidate frontier未发布且joint AC调用数为0。v1 invalidation manifest为`7ac6a6a2ecc76304376654b36d6a0e83e5bd506e9f3ff537356fa13ad94ac3dd`。v2只修正该输入验证，并在每小时前置校验`BUS_TYPE in {PQ,PV,REF}`及恰好一个`REF`；真实baseline的24小时、73台committable和72台reserve provider通过零求解器preflight，但正式进程约`46725 s`后仍无checkpoint、frontier、joint AC调用或可用求解进度日志，已按用户授权停止。termination manifest为`e8bcef7466a1dfa44e4c0a444eb297fbf7160cf1f7596485c86a6fd9984b799b`；停止不是不可行证据且v2不得恢复。

V3的求解器与算法选择在正式结果前完成。当前自动许可证下只有HiGHS 1.15.1通过正式模型容量门；1/4/8线程冻结重复pilot按不读取目标值的规则选择4线程。随后单体全状态MILP与exact selected-state constraint generation各重复两次：exact-CG以`54.057/54.502 s`两次通过最终24状态审计，单体两次到时限且实际认证区间宽度均为`0.003796157`，因此选择exact-CG。solver/formulation result manifest分别为`4b05c7d7fcbd8f64ddb9eb61d4ee15c571a7905d8ebd453ac19d07cbf56c63d1`和`82f1f0cb72d574b2054f193f6354383c5629bd30796b42a919323ef326c0d7e1`。

V3的proxy与cost阶段都从同一冻结seed独立启动exact-CG；每个master后重新筛查全部inactive state，`unresolved`一律标记为`unresolved_promoted`并加入active set，不得作为不可行证据。每阶段最终都必须固定同一shared snapshot，对全部24状态求LP并独立审计整数、功率平衡、潮流、额定、组合、ramp、备用和安全响应残差。

proxy最大化的最终证书定义为`LB=q_feasible_full_state`、`UB=min(valid active-master dual bounds)`；cost最小化定义为`LB=max(valid active-master dual bounds)`、`UB=C_feasible_full_state`。统一使用`absolute_gap=UB-LB`和`incumbent_relative_gap=absolute_gap/max(abs(feasible incumbent),1e-12)`。actual区间随真实可行界与对偶界更新，但target relative gap `1e-4`、maximum accepted relative gap `1e-3`和proxy maximum accepted absolute gap `1e-3`均在正式运行前冻结；达到最大门但未达到target只能标为`eligible_within_maximum`，不得写成target attained，也不得按结果修改时限或阈值。

正式资格只读取stage顶层的`target_attained`、`eligibility_status`和`maximum_acceptance`，它们使用上述incumbent-relative gap。嵌套的`certificate.relative_gap`和`certificate.target_gap_attained`使用通用辅助尺度`absolute_gap/max(abs(LB),abs(UB),1)`，只作诊断且不得作为V3资格或论文target标签。cost阶段结束后还必须通过`primary_proxy_regret`：最终commitment相对第一阶段认证proxy上界的regret既不得超过`stage1_absolute_gap + 1e-7 + 1e-6`，也不得超过`0.0010011`；最终candidate残差审计也必须通过。

每个V3事件都对JSONL执行flush与fsync；每次`solver.solve`期间有30秒heartbeat，每次HiGHS调用保存独立原生日志，配置的5秒值只是MIP报告行的最小间隔，不保证每5秒产生一行。六个预算候选各自使用同目录原子rename发布checkpoint，并在resume时验证identity、完整文件集合、manifest、stage certificate、primary regret和最终审计；冻结父基线不写candidate checkpoint。只有六个预算候选全部完成并原子发布包含父基线的完整requested frontier后才允许joint AC；不得跨candidate、初值、solver或formulation拼接见证。V3 preregistration/input-contract SHA-256分别为`01646721d15395668bf0079cb6fe218dc0625187d1fbf108c5db74e47ae33f88`和`af4a388d80c211611a8e1dad3861936decb7f3c3e2de3a422116c87c013d8aa0`。

历史V3 attempt `formal_20260719T061959Z`已停止且不得恢复；它没有发布六个预算checkpoint和完整frontier，也不构成数学不可行或无解证据。`repair_005`已发布4/6个checkpoint后在candidate 5运行性中断，当前无solver进程；旧attempt不得resume，后续必须使用新attempt ID和新output root重新取得lease。只有六个预算checkpoint、包含冻结父baseline的完整frontier、manifests、两阶段certificates、primary regret和final 24-state audit全部发布并验证后，才允许joint AC。因此`treatment_followup_gate_passed=false`；此前保持`ac_security=false`、`security_certified=false`、`full_m6_model_input_ready=false`和`formal_vma_published=false`，停止依赖该对照的treatment及论文结果固定。

## 13. 规格编码门槛与当前状态

以下门槛用于约束后续编码；M0/M1电网安全基础、M2确定性扩建、M3固定F/X策略、M4 B0-B2基线、M5a/M5b随机基线、M5c固定政策合成holdout门、M6b接口门、具名原生RTS-GMLC 6小时/24小时后端、多POI共同状态比较、amendment-004 direct AC及零注入恢复诊断已经实现。AC-aware commitment的exact-CG runner、动态界证书、monitor、durable日志、原子checkpoint和resume门已经实现；`repair_005`已发布4/6个checkpoint后在candidate 5运行性中断，当前无正式candidate-generation进程；旧attempt不得resume，也不能写成V3或V4结果已完成。M5c只给出平衡确定性holdout适应性值与失败区域；原生DC结果只给出公开benchmark的日前selected-N-1运行见证，direct与zero-control AC结果均明确以0 secure关闭直接通过门，恢复诊断仍未见证h15/h21。它们都不构成正式经验VMA、频率、保护、工程AC或完整逐时运行认证：

- 每个公式的功率、能量和时间单位一致；
- 所有规划、短期、小时和事故索引在符号表中定义；
- 实际服务和合同容量校核均闭环；
- 工程投运不读取未来延期信息；
- F在规定状态下不可网络削减；
- X响应前/后安全采用何种数据和模式已经在配置中决定；
- B2、B3、B4和B6只存在声明过的结构差异；
- 指标计算不依赖求解方法名称或手工判断。

### 13.1 量纲审计

| 关系 | 左侧单位 | 右侧单位 | 结论 |
|---|---|---|---|
| IT及电网侧需求 | MW | rack × p.u. × kW/rack ÷ 1000；PUE × MW | 一致 |
| 服务平衡 | MW | 需求、削减、缺口和恢复功率 | 一致 |
| 节点功率平衡 | MW | 发电、负荷和支路潮流 | 一致 |
| DC支路方程 | MW | MW/rad × rad | 一致 |
| 恢复债务递推 | MWh | MWh + MW × h | 一致 |
| 事件/季度能量预算 | MWh | occurrence × MW × h | 一致 |
| 小时CFE | MW | 归属功率与数据中心功率 | 一致 |
| 年度CFE | MWh | occurrence × MW × h | 一致 |
| 运行成本 | currency | currency/MWh × MW × h | 一致 |
| unused容量 | MW-year | MW × h ÷ 8760 | 一致 |

## 14. 尚需数据确认的风险

1. RTS-24提供`RATE_A/B/C`，但没有给出与本研究响应前/后时序对应的持续时间映射；当前短时支路态固定正常出力并使用C，持续态使用A及显式纠正边界，正式认证前必须补充来源并决定B的用途。
2. M2只实现既有branch 11/12的合成热增容，并与POI增量一起作为一个捆绑走廊工程；新增主变/并联回路的电纳和热限额仍未映射，不能只增加POI标量上限而忽略上游潮流。
3. 业务响应、持续时间和恢复参数目前主要来自公开实证范围，必须做多档敏感性而不能声称代表特定企业。
4. CFE地域和归属规则必须在实验前冻结；不同规则不能混在同一“小时级CFE”标签下。
5. 接入延期、业务损失和扩建成本参数可能影响T指标，需要预注册范围和物理结果对照。
6. 现有RTS-24纠正上界是`Pmax`比例的合成灵敏度，不含响应时间证据；原生RTS-GMLC 6小时benchmark使用其自身ramp，但该字段不能回填RTS-24。RTS-24 branch 10（7-8）非计划孤岛仍未解决。
7. branch 4/9/26对应的热额定值、无功补偿和纠正开断只是候选补救，正式使用前需要工程参数、安装状态和控制时序证据。
8. RTS-GMLC Area 1映射到RTS-24的四负荷快照是load-only代理，不是逐时负荷/新能源验证。固定全在线时最低快照858.81 MW低于`Pmin`合计1036 MW，全年有1416/8784小时低于该阈值。当前静态选择使四快照的107态均可行，但四个组合彼此独立，未使用启动成本、最小开停机时间和跨时爬坡；它们仍需自己的时序SCUC或有来源的外生组合，不能加入系统负荷松弛掩盖。独立原生RTS-GMLC 6小时结果不回填或升级这四个快照。
9. 静态选择的AC复核已映射缩放P/Q负荷、停机正有功机组、同步调相机和动态REF。四个正常态均通过最小偏差AC恢复，但尚未对每个快照的全部107个事故态执行同样复核。65切点成本下包络用于选择组合，保存的精确多项式成本仅是选定解回算值。
10. M2的bus 8 POI、2季度工期、branch 11/12增容量、250 MW申请规模及成本权重均是冻结的合成机制参数，不是场址证据。成本未统一到真实币值基准年；扩建只给出DC MW热限增量，缺少AC MVA、无功和电压工程参数，因此当前428个状态-季度通过仅是DC约束验收。
11. M3固定政策的F/X路径、75 MW条件容量上限、连续包络、响应和恢复参数均为机制参数。856个actual/contract-counterfactual状态行和28248个逐机组行可证明已建模DC约束成立；8784小时压力轨迹另证明当前满合同基线发生正X调用后没有恢复头寸。两者都不能证明真实事件频率或AC安全。`minimum_call_certificate_mw_sum`是跨互斥事故及两层的求解平局指标，不是运营功率、能量或期望成本。
12. M3合同层可独立选择反事实正常调度；它证明相同外生条件下存在可交付调度，不证明从actual当前调度立即迁移。M3固定策略已改为原始凸二次目标的直接数值QP、原约束审计和L1线性可行性投影；变量移动与目标偏差包络只用于数值可行性验收，不是最优间隙或误差证书，没有对偶间隙证书时不称数学精确全局最优。M2完整枚举不启动及每个固定启动季度，并对各候选直接数值求解原始凸QP、审计原约束和线性修复；有限枚举已解除PWL/MIQP依赖，但同样不能在没有显式最优间隙证书时称数学精确全局最优。正式B0-B2采用主接入缺口最优面上的最小/最大X暴露区间，不用任意微小价格识别唯一拆分。
13. M4 B0-B2冻结比较只完成合成DC机制门；具名原生RTS-GMLC已完成6小时/24小时日前selected-N-1 DC耦合、多POI共同状态比较、两个代表POI的amendment-004 direct AC sensitivity及零注入normal恢复诊断。direct与zero-control均为0 secure，且官方电压边界内h15/h21仍未取得共同可行性见证；现有路径也不包含Q-limit switching、工程接入设备或有来源的tap/shunt/补偿控制。full N-1、实时SCED、工程级AC恢复/认证、响应与频率证据、RTS-24 branch 10保护/孤岛处置、扩建MVA/无功/电压与控制参数及真实业务恢复轨迹仍未闭环；在这些阻塞解除前，所有结果必须保持`treatment_followup_gate_passed=false`、`ac_security=false`、`security_certified=false`和`full_m6_model_input_ready=false`，不得升级为场址、合同或运行认证。
