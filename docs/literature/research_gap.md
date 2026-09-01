# 研究缺口与贡献定位

更新日期：2026-08-25
适用范围：当前已编码学术文献与官方制度来源；不等同于投稿前的穷尽式系统综述

## 一页结论

当前证据能分别建立两个制度对象：FERC 195 FERC ¶ 61,216 及其引用的
PJM precedent 表明，愿意且能够限制withdrawal的大负荷可以采用MW contract
level与控制/保护措施约束网络侧取电；EnergyTag标准和Google官方24/7 CFE材料
表明，数据中心用电可以按小时与属地CFE及PPA做ex-post matching/accounting。
这些来源没有证明某个具名data center把**同一份workload flexibility**同时承诺给
两者，也没有给出这种行为的发生率或因果影响。因此，论文只能把二者的潜在交集
称为`contract-overlap hypothesis`（可检验的制度交集风险），不能陈述为已经观察
到的普遍双重签约事实。逐项边界见`contract_evidence_matrix.csv`。

最近邻又收紧了方法优先权边界。Fan and Zhao (2026, DC14)已经联合优化
workload distribution与regulation capacity commitment，并用chance constraints
与VaR queue constraints约束瞬时和累计可交付性；Khanal et al. (2026, DC15)
已经把firm/flexible/interruptible tiers及depth、duration、ramp、recovery和年度
上限放入PJM/Korea capacity expansion。故论文贡献不能写成容量承诺、
deliverability、容量扩展中的event-shape/recovery或sharp optimal-transport bound
本身。当前可守的候选组合是：

1. 把network-contingent claim与hourly-CFE claim表示为两个分离制度义务，并检验
   它们是否映射到同一temporal workload envelope；
2. 用B6 double-counting counterfactual表示“分别按完整包络记账”的错误机制，
   与共享包络模型公平比较；
3. 在only-public-marginals、unknown joint law下，报告minimum-flexibility
   underprovisioning等estimand的sharp partial-identification application，并把
   exogenous grid infeasibility、solver unresolved与服务欠交付分开。

这个组合仍是**待证的研究设计**，不是已有经验结论。冻结70-cell formal phase-map
必须同步保留：`R1=0, R2=0, R3=69, mixed=1, unresolved=0`；original positive H2
unsupported。当前`formal_execution_ready=false`，文献更新不提升实验gate或
认证状态。

## 最近邻与优先权边界

| 证据 | 已解决的内容 | 对本文主张的约束 | 仍可检验的差异 |
|---|---|---|---|
| Fan and Zhao (2026, DC14) | 时空工作负荷与调频容量承诺联合优化；瞬时chance constraints；累计RegD窗口的VaR queue约束；modified IEEE 68-bus、PJM、Alibaba traces | 不以regulation capacity commitment或deliverability本身主张方法优先权 | 未构造network-contingent与hourly-CFE两项制度义务对同一包络的B6反事实，也不处理跨源公开边缘的未知联合律 |
| Khanal et al. (2026, DC15) | PJM/Korea容量扩展中的firm/flexible/interruptible tiers；depth/duration/ramp/recovery/annual caps | 不以capacity expansion中的event-shape或recovery本身主张方法优先权 | 其RPS/CO2政策不是数据中心买方hourly-CFE matching，也未研究两类义务的共同资源映射与部分识别 |
| Wan and Li (2026, DC04)、Wan, Fang and Li (2026, DC11)、Ma et al. (2025, DC12) | 单一统一调度变量下的拥塞缓解、时空移峰和新能源消纳 | 不把“联合网络与清洁能源目标”包装成贡献 | 单一物理变量天然避免重复计数；本文需要检验分离制度记账是否会在共同包络上制造差异 |
| Williams et al. (2026)、Radovanović et al. (2023)、Lin and Chien (2025, DC13)、Zhang et al. (2025, FLEX09) | 实证削减响应、碳感知调度、负荷解耦、传输受限风险 | 实证flexibility或碳感知调度本身不形成本文优先权 | 尚未给出可审计的“同一workload population—两项义务”映射 |

## 制度证据链及其边界

| 制度对象 | Primary source能支持什么 | 不能推出什么 |
|---|---|---|
| Network-side flexible load contract | FERC 195 FERC ¶ 61,216支持flexible large loads在规定条件下限制withdrawal；其PJM precedent包括interim NITS及firm/non-firm contract-demand transmission service，服务至specified MW contract level，并以控制/保护措施限制取电 | 不支持hourly CFE claim；不识别同一内部workload；不证明双重签约、发生率或因果影响 |
| Granular/hourly CFE accounting | EnergyTag支持ex-post、同一时间间隔、至少小时级的certificate-to-consumption matching，并要求hourly/subhourly production与consumption data | 不构成网络应急服务或物理可调用容量；不证明共同包络或双重签约 |
| Data-center 24/7 CFE practice | Google官方方法与案例支持按小时把facility consumption与regional CFE、区域PPA和grid mix联系 | 属企业方法与实例，不证明某一workload同时承担network-side contract，也不识别overlap incidence |

证据层级必须逐级升级：`institutional_objects_separately_supported`是当前状态；
`same_resource_overlap_observed`需要合同、计量与workload/resource mapping；
`overlap_frequency_or_causal_effect_identified`还需要抽样框、联合时钟和可复核对照。
同一公司同时出现在两类公开材料中，不足以证明同一物理资源被重复承诺。

## Problem–Method–Insight

| 结构 | 当前限定 |
|---|---|
| Problem | 在两类制度对象分别存在、但缺少共同资源映射的条件下，检验它们若同时索取同一temporal workload envelope，是否产生minimum-flexibility underprovisioning或服务欠交付；不预设现实中已经发生重叠 |
| Method | 冻结共享包络correct model与B6 double-counting counterfactual，在相同输入、安全集和holdout上比较；当只观察到grid/workload公开边缘时，在transport polytope上计算sharp conditional bounds；保留right-censoring、solver-unresolved和exogenous infeasibility |
| Insight | 可报告的是“哪些可观测边缘与结构假设足以排除、容许或迫使风险”，以及什么新增联合数据会收窄识别区间；不能把算法工具或合成敏感性直接升级为工程、合同或普遍行为结论 |

T1–T3的定义、证明草图、tight/反例和外推边界见
[`rq2_theoretical_propositions_v1.md`](../model_spec/rq2_theoretical_propositions_v1.md)。
这些派生命题不替代经验P1–P3，也不改变冻结v6合同或当前负结果。

## 可证伪命题与所需数据

| 命题 | 支持观察 | 推翻或削弱观察 | 仍缺数据 |
|---|---|---|---|
| P1(`S`)：在结果前冻结的具名设施/项目`U`，或预注册抽样总体`S`内，至少一个分析单位把两项义务映射到同一temporal workload envelope | 对同一`U`，或`S`中预先定义的单位，用network contract、hourly-CFE obligation、共同计量窗口和内部workload/resource mapping证明同时占用；不得在看过证据后更换`U/S` | 对具名`U`，完整可审计映射证明资源、负荷池或时段隔离；对有限总体`S`，按预注册覆盖规则完成全部单位核验且均无共同映射。单个隔离案例不能推翻总体外的存在性，缺失映射只能记为unresolved | `U/S`定义与纳入规则、合同条款、事件通知、facility meter、workload queue/dispatch及资源分池记录 |
| P2：冻结主estimand `Δ=D_min^flex,correct-D_min^flex,B6`的all-coupling robust正效应 | 在冻结coupling set上，sharp lower bound满足`LB_Δ>0`，且预注册抽样/稳健性门通过；这才支持B6产生严格正的normalized minimum flexibility underprovisioning | `LB_Δ<=0<UB_Δ`中的nonpositive witness已经排除all-coupling robust正主张，但现实未知coupling的符号仍partially identified；`UB_Δ<=0`进一步排除任一admissible coupling上的严格正效应。必要arm上B6不劣或预注册稳健性失败本身只表示正经验主张未建立，不能在没有相应bound witness时写成反证 | 有现实时间戳的network calls、hourly-CFE calls、恢复轨迹、训练/holdout分离样本及完整coupling witnesses |
| P3：部分识别区间在声明条件下是sharp且可复核 | 完整Cartesian outcomes、primal/dual一致、coupling witness可重建端点，且无未决单元被当成不可行 | 缺失组合、duality gap或witness失败；timeout/local failure被误写成infeasible；结构约束改变后端点不再可达 | 完整结果矩阵、边缘权重、联合约束来源、求解证书与provenance |

P1(`U/S`)失败时，只能否定该预注册单位或总体内的命题；不得由一个隔离案例外推
为全球不存在，也不得在结果后换总体。P1未决时，应把论文改写为条件制度设计/
压力测试，不得再用现实重叠作为动机事实；
P2中`LB_Δ<=0<UB_Δ`应报告为真实coupling符号部分识别，同时明确all-coupling
robust正主张已被nonpositive witness排除；`UB_Δ<=0`进一步排除集合内任一严格
正效应。必要arm不满足或预注册稳健性失败应报告“正主张未建立”。不能看过结果
后调整阈值制造阳性；
P3失败时，只能报告已验证的非sharp区间或未决状态。

## Introduction可用的条件化贡献表述

> Network-side flexible-load arrangements and hourly carbon-free-energy
> accounting are separately documented institutional objects, but public
> primary evidence does not yet establish that a named data center commits the
> same workload-flexibility envelope to both. We therefore treat their overlap
> as a falsifiable hypothesis. We compare a shared temporal-envelope model with
> a B6 double-counting counterfactual and, when only public marginals are
> observed, characterize sharp conditional bounds on flexibility
> underprovisioning under an unknown joint law. The design does not claim that
> overlap is prevalent, that interconnection capacity X is overstated, or that
> the present evidence establishes a positive empirical effect.

## 优先权与外推边界

- 容量承诺、瞬时/累计deliverability、capacity expansion中的event-shape与recovery，
  均已有最近邻覆盖。
- 多阶段随机规划、robust/CVaR、N-1、年度与24/7 CFE比较、optimal transport
  与sharp bounds是方法背景，不能单独承载贡献。
- `y_CFE`表示同小时可归属清洁电量，不追踪流向数据中心的电子。
- 合成机制、derived network need或公开边缘重放不构成工程安全、监管合规或市场
  发生率认证。
- timeout、local solver failure、missing incumbent或incomplete certificate不证明
  数学不可行。
- frozen result、原始负结论和`formal_execution_ready=false`必须与论文叙事同步；
  文献更新不允许触发结果后调参。

## 下一步证据获取

1. 公开路径：继续检索具名data center的flexible transmission/interconnection
   agreement、curtailment tariff、24/7 CFE披露及可连接的计量边界；未建立共同资源映射
   前保持P1未证。
2. 合作方路径：请求去标识化合同能力、触发时间、actual calls、workload queue、
   recovery与hourly-CFE schedule；预先定义资源映射和train/holdout切分。
3. 计算路径：只执行已冻结v6协议，完整报告70-cell负结果；在新的外部证据支持
   新设计前，不调整同一网格、阈值或主张方向。
