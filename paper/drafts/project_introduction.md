# 达产与扩建延期不确定性下智算中心分阶段接入与小时级绿电协同规划

## 1 摘要

网络条件服务与小时级无碳电力（carbon-free energy, CFE）匹配会同时占用数据中心可延期、可恢复的计算任务。两项服务分别可行，并不保证它们在同一业务时序包络中能够共同交付。本文研究：网络安全调用保持为硬约束时，逐步提高小时级CFE目标会怎样改变最低业务柔性需求，联合时序会形成额外需求还是组合缓解，以及分离记账相对正确联合规划产生何种容量偏差。

本文在相同输入、安全集合和求解标准下设置network-only、CFE-only、joint-correct与joint-B6四个arms。四个arms共享完整24h、zero-carry-in窗口、训练支持和holdout执行规则；包络联合约束瞬时功率、最大持续时间、事件次数、累计能量、恢复功率和恢复债务。CFE服务请求使用注册目标对应的完整缺口，恢复功率同时受业务headroom和同小时CFE盈余约束。对每个注册CFE目标，分别计算最低归一化柔性\(D_N,D_C,D_B,D_J\)，并将联合时序交互分解为
\(I_{joint}=D_J-\max(D_N,D_C)=I_{sep}+A_{B6}\)，其中
\(I_{sep}=D_B-\max(D_N,D_C)\)，\(A_{B6}=D_J-D_B\)。完整事件包络下不预设四臂容量顺序，正负差值分别表示额外需求、组合缓解、B6低配或B6高配。
B6容量冻结后进入共享物理包络回放，以评估hard-grid failure、CFE shortfall和联合服务损失。

确认性设计包含36个`hourly_cfe_target × flexible_fraction × recovery_headroom`全因子cells与10个时序参数OAT cells，共46个。公开网络/CFE块与业务块的配对不确定性在holdout稳健性层通过离散transport polytope处理；主容量证据来自共同代表点和完整training Cartesian support审计。当前样本均为完整24h blocks，E0外生电网不可行、service shortfall和solver unresolved分别编码。首篇研究聚焦联合服务可交付前沿与不足归因；多阶段F/X接入、电网扩建延期以及年度/小时CFE对规划决策的影响作为项目后续扩展。

**关键词：**智算中心；网络条件服务；小时级CFE；业务柔性；可交付前沿；联合服务；固定策略回放

## 2 研究现状

### 2.1 两类制度对象及 contract-overlap hypothesis

FERC 195 FERC ¶ 61,216 及其引用的 PJM precedent 表明，愿意且能够限制 withdrawal 的大型负荷可以按指定 MW contract level 接受网络侧服务，并由控制或保护措施执行取电边界。EnergyTag Granular Certificate Matching Standard 与 Google 24/7 CFE 方法支持按同一时间间隔、规定地域和计量边界开展小时级 CFE 的 ex-post accounting/matching。两条证据链分别支撑 network-contingent service arrangement 与 hourly-CFE accounting/matching；共同合同、计量和内部工作负荷映射仍需直接证据。因此，本文把两类义务对同一 temporal workload envelope 的潜在交叠登记为可证伪的 contract-overlap hypothesis。

### 2.2 灵活接入与电网容量规划

数据中心接入研究已覆盖候选站址、容量分配和互联扩展。Kim、Dong和Xie[1]把 firm、pause 与 shift 包络纳入规划者主动选址和逐时单故障筛选，说明柔性可改变候选接入点评价；Chen和Zheng[2]在投资—逐时运行模型中比较工作延期、时移和跨节点转移对互联容量扩展的影响。Li、Fang和Chen[3]将 robust firm capacity、CVaR flexible capacity 与位置属性用于静态输电容量分配，Mytton等[6]则从电网容量压力和治理流程说明大型数据中心接入的现实约束。这些工作建立了 flexible interconnection 和 grid-capacity planning 的直接基础。本文首篇聚焦分离制度义务的共同业务资源；固定POI下的多阶段F/X释放、扩建工期与延期保留为项目扩展。

### 2.3 需求响应、碳感知计算与工作负荷包络

Wierman等[13]系统梳理了数据中心需求响应的技术机会与运营约束，Liu等[14]研究了公用事业峰值需求响应中的工作负荷调节和成本。Goiri等的 GreenSlot[15]以及 Parasol and GreenSwitch[16]分别以批作业调度和系统协同利用现场可再生能源；Qureshi等[17]通过跨地域路由利用电价差，Liu等[18]通过 geographical load balancing 跟随可再生能源供给。Radovanović等[19]进一步用区域碳强度形成逐时 virtual capacity curve，建立了实际数据中心的 carbon-aware computing 路径。

资源约束方面，Kwag和Kim[20]说明需求响应需要超越单一静态MW上限；Crozier和Liska[7]综述了保护、预冷、CPU/GPU调节和作业调度等柔性来源；Williams等[5]以GPU集群和推理业务实证分析快速响应与持续削减。上述研究支撑工作负荷可调性及功率、持续时间和恢复参数的技术边界。本文把这些既有机制组织进两项义务共享的完整 24h、zero-carry-in 窗口内时序包络，并以B6反事实检验分离规划的后果。

### 2.4 统一调度下的网络—新能源协同与可交付性

Wan和Li[4]把数据中心时空负荷灵活性纳入 security-constrained unit commitment，在统一调度变量下缓解拥塞并促进新能源利用。Wan、Fang和Li[26]的 arXiv:2511.08759 于2025年发布v1、2026年更新v2，以单一空间重分配变量分析拥塞、弃电与成本；Ma等[27]用内生节点价格驱动时空移峰；Lin和Chien[28]研究多站点 load decoupling 资源的碳收益分配；Zhang等[29]则刻画输电约束如何降低柔性资源的可用性。这些工作正面建立了统一物理调度下的网络—新能源协同基准。

Fan和Zhao[30]联合优化 workload distribution 与 regulation capacity commitment，并以 chance constraints 和 queue-VaR constraints 约束 instantaneous/cumulative deliverability。Khanal等[31]在PJM和韩国容量扩展中建模 firm/flexible/interruptible tiers，以及 depth、duration、ramp、minimum recovery、年度能量和小时上限。因此，capacity commitment、deliverability、event shape 和 recovery 已有明确优先权。本文聚焦固定网络安全调用下、随小时级CFE目标变化的完整时序可交付前沿，并用四臂有符号分解区分单服务瓶颈、联合交互和B6容量偏差。

### 2.5 多阶段输电扩展与鲁棒规划

Han、Kim和Lee[8]用场景树研究需求不确定性下的长期多阶段输电扩展；Webster[9]提出广域多阶段随机输电扩展算法；Akhavizadegan、Wang和McCalley[10]研究迭代随机扩展中的场景选择。Jabr[11]处理新能源与负荷不确定性下的鲁棒输电扩展，Li等[12]进一步把多重不确定性和主动负荷纳入规划。这些研究为场景树、非预见性、鲁棒性和扩建决策提供方法基础。项目后续扩展将这些方法用于固定POI的数据中心达产、F/X释放和工程延期，但不把多阶段规划或鲁棒优化本身作为首篇贡献。

### 2.6 年度匹配、小时级CFE与清洁计算

de Chalendar和Benson[21]指出年度100%可再生能源声明不能完整反映用电时段与系统脱碳；Miller、Novan和Jenn[22]量化了小时核算与年度/月度聚合之间的差异。Riepin和Brown[23]比较年度与24/7 CFE采购的成本和系统影响，Riepin、Jenkins、Swezey和Brown[24]分析24/7匹配对先进清洁技术部署的影响。Riepin、Brown和Zavala[25]进一步联合优化计算负荷的时空转移，以提高计算活动与清洁电力在时间和空间上的一致性。这些工作构成年度/小时核算、采购与清洁计算调度的直接基准。本文在此基础上研究分离的网络条件义务与小时CFE义务是否索取同一业务包络。

### 2.7 联合可交付前沿、归因与稳健性

本文把研究对象定义为固定网络安全调用下、随小时级CFE目标变化的业务柔性需求前沿。四臂设计先识别network-only和CFE-only中更严格的单服务，再计算joint-correct相对单服务的有符号联合交互，并用joint-B6分解其容量偏差。RTS-GMLC网络/CFE块与Alibaba业务块的配对不确定性只影响holdout风险汇总：independent、comonotone和countermonotone pairing作为诊断点，完整离散transport polytope给出条件sharp bounds；多指标结论要求同一个coupling见证。阴性结果、E0和unresolved状态均进入可审计证据链。

![图1 当前研究现状与本项目定位](../figures/project_literature_landscape_cn.svg)

**图1 当前研究现状与本项目定位**。基于本文审阅的31篇学术文献所作的结构化定位，不是穷尽性 bibliometric result；三项制度资料仅支撑两类对象分别存在，不证明现实 contract overlap。

## 3 首篇贡献与项目扩展

### 3.1 首篇贡献A：联合业务柔性的离散可交付前沿

本文固定网络安全调用，在四个预注册小时级CFE目标、三档业务柔性比例和三档恢复headroom上计算完整时序包络的最低柔性需求。四臂使用相同输入、安全标准、训练支持和solver contract。该设计给出单服务分别可交付时，联合服务何时需要额外柔性、何时因事件合并形成组合缓解的离散边界。

### 3.2 首篇贡献B：四臂加法归因与固定策略后果

本文把联合交互写成
\(I_{joint}=I_{sep}+A_{B6}\)：\(I_{sep}\)表示B6分离包络相对单服务的交互，
\(A_{B6}\)表示B6相对correct的有符号容量偏差。容量冻结后，correct与B6策略统一进入共享物理包络回放，分别报告hard-grid、CFE和联合服务失败。公开边缘transport用于检验这些holdout后果对允许配对的稳健性；E0、service shortfall与solver unresolved保持分离。

### 3.3 项目扩展：多阶段 F/X—扩建—年度/小时 CFE

后续项目在首篇机制与识别链之外，研究数据中心达产、电网工程工期与延期逐步揭示时的非预见性多阶段 F/X 释放和扩建决策，并比较年度与小时 CFE 对接入容量、扩建时序和柔性分配的影响。该扩展形成包含 F/X、建设 lead time、正常态与关键 N-1、年度/小时匹配的长期研究蓝图。

## 4 研究目标与主要内容

### 4.1 首篇目标

在网络安全调用保持为硬约束时，刻画小时级CFE目标变化对应的业务柔性可交付前沿，分解单服务瓶颈、联合时序交互和B6有符号容量偏差，并检验冻结策略的场景外服务后果。

### 4.2 主要内容

1. 在四个注册小时级CFE目标上构建network-only、CFE-only、joint-correct和joint-B6四臂；
2. 计算\(D_N,D_C,D_B,D_J\)并验证\(I_{joint}=I_{sep}+A_{B6}\)；
3. 完成36-cell主factorial和10-cell时序OAT的完整training-support审计；
4. 在holdout上回放只使用当前可见状态的冻结策略，分别记录hard-grid、CFE和联合服务风险；
5. 在finite-grid support上计算服务风险transport bounds与共同coupling witness，并单列无条件E0质量；
6. 完整报告positive、negative、infeasible和unresolved cells；
7. 在后续项目中扩展到多阶段F/X、扩建时序及年度/小时CFE对照。

图2  项目总体研究流程

![项目总体研究流程](../figures/project_workflow_cn.svg)

图3  智算中心与电网协同网络结构

![智算中心与电网协同网络结构](../figures/project_network_cn.svg)

## 5 项目可行性与当前状态

### 5.1 数据、模型与复现基础

项目已形成 RTS-GMLC 24 小时网络/CFE blocks 和 Alibaba 24 小时 workload blocks 的分源、版本化数据包，训练/holdout 严格分离。当前主样本全部是完整 24h、zero-carry-in blocks；尚无跨日 carry-in linkage，也没有当前样本中的 right-censored block。实现已覆盖 E0 判定、完整 training-support 审计、minimum-flexibility 规划、B6 分离规划/共享执行、固定策略回放、transport bounds、共同 coupling feasibility、四臂增强基线的 validate-only 接口，以及按 block 隔离的 formal bootstrap/controller、checkpoint、resource journal 和 manifest 契约。新的46-cell联合可交付前沿v2协议已seal并等待独立R4 review；target-specific CFE builder、前沿归因payload和正式runner尚待versioned implementation successor。配置、solver certificate、残差和工件均按版本与 SHA-256 审计。上述实现与 validate-only 能力仅证明代码路径和关闭门禁可检查，不等于正式实验已经执行，也不构成正式结果、论文结论或安全认证。

### 5.2 既有证据与当前执行状态

冻结70-cell/旧formal-batch derived benchmark完整保留为 R1=0、R2=0、R3=69、mixed=1、unresolved=0；original positive H2 unsupported。该结果是阴性或边界证据，不能通过结果后调参改写。

固定顺序 `holdout_s20260822_0008 → holdout_s20260822_0009` 的 V8 nonformal two-block pilot 已分别取得 pre-run independent PASS 和 post-result independent PASS；该证据只关闭此次非正式 pilot 的对应门禁，不授予 formal execution authority。Formal activation V1–V4 均未取得执行许可，V4 现仅作为 historical `ESCALATE` 记录保留。当前没有V5 activation candidate，也没有独立activation PASS或user formal-run authority。

因此，1071-block grid、后续 pairwise replay 和 identification 均未运行或发布；formal result、paper claim 和 security certification gates 全部保持关闭。TimeLimit、resource stop、unresolved、缺失 incumbent 或不完整 certificate 均不构成 mathematical infeasibility。以上仅为项目执行状态，不作为论文结果。

## 6 预期成果与研究边界

### 6.1 预期成果

1. 网络安全调用下、随小时级CFE目标变化的四臂最低柔性需求曲线；
2. \(I_{joint}=I_{sep}+A_{B6}\)的有符号容量归因与bottleneck vector；
3. B6与correct固定策略的hard-grid、CFE和联合服务后果；
4. 对当前完整24h blocks保留E0、服务短缺与未决状态的holdout证据链；
5. 作为后续项目扩展的多阶段 F/X—扩建—年度/小时 CFE 模型。

### 6.2 研究边界

本文主estimands是按\(D_{DC}\)归一化的\(D_N,D_C,D_B,D_J\)及其有符号联合交互分解，不解释为条件容量X高估。公开边缘上的holdout bounds是相对于声明transport polytope的条件稳健区间，不是现实合同发生率、真实违约概率或因果效应。selected-N-1 DC benchmark用于规划与机制分析，不构成工程安全认证。CFE表示同小时、规定地域内可归属清洁电量的核算/匹配，不追踪流向数据中心的电子。

## 7 参考文献

[1] Kim, D., Dong, L. and Xie, L. (2026). “Flexibility-aware framework for efficient planner-initiated siting of data center.” Nature Communications. https://doi.org/10.1038/s41467-026-72324-9

[2] Chen, Y. and Zheng, X. (2026). “To Defer or To Shift? The Role of AI Data Center Flexibility on Grid Interconnection.” ACM Sustainability Week. https://doi.org/10.1145/3765611.3815593; https://arxiv.org/abs/2604.05376

[3] Li, S., Fang, B. and Chen, C. (2026). “Risk-Aware Allocation of Transmission Capacity for AI Data Centers.” arXiv preprint arXiv:2604.08854. https://arxiv.org/abs/2604.08854

[4] Wan, H. and Li, X. (2026). “Data Center Spatio-Temporal Load Flexibility in Security-Constrained Unit Commitment for Enhanced Grid Efficiency and Reliability.” arXiv preprint arXiv:2605.18517. https://arxiv.org/abs/2605.18517

[5] Williams, C., Colangelo, P., Coskun, A. et al. (2026). “Power-Flexible AI Data Centers: A New Paradigm for Grid-Responsive Compute.” arXiv preprint arXiv:2606.25098. https://arxiv.org/abs/2606.25098

[6] Mytton, D., Ashtine, M., Wheeler, S. and Wallom, D. (2023). “Stretched grid? Managing data center energy demand and grid capacity.” Oxford Open Energy. https://doi.org/10.1093/ooenergy/oiad014

[7] Crozier, C. and Liska, M. (2025). “The Potential of Data Center Energy Demand To Provide Grid Flexibility.” Current Sustainable/Renewable Energy Reports. https://doi.org/10.1007/s40518-025-00258-9

[8] Han, S., Kim, H.-J. and Lee, D. (2020). “A Long-Term Evaluation on Transmission Line Expansion Planning with Multistage Stochastic Programming.” Energies. https://doi.org/10.3390/en13081899

[9] Webster, M. (2022). “A Multistage Stochastic Transmission Expansion Algorithm for Wide-Area Planning under Uncertainty.” Technical report. https://doi.org/10.2172/1737833

[10] Akhavizadegan, F., Wang, L. and McCalley, J. (2020). “Scenario Selection for Iterative Stochastic Transmission Expansion Planning.” Energies. https://doi.org/10.3390/en13051203

[11] Jabr, R. A. (2013). “Robust Transmission Network Expansion Planning With Uncertain Renewable Generation and Loads.” IEEE Transactions on Power Systems. https://doi.org/10.1109/TPWRS.2013.2267058

[12] Li, W., Zhao, L., Bo, Y. et al. (2021). “Robust transmission expansion planning model considering multiple uncertainties and active load.” Global Energy Interconnection. https://doi.org/10.1016/j.gloei.2021.11.009

[13] Wierman, A., Liu, Z., Liu, I. and Mohsenian-Rad, H. (2014). “Opportunities and Challenges for Data Center Demand Response.” 2014 International Green Computing Conference, pp. 1–10. https://doi.org/10.1109/IGCC.2014.7039172

[14] Liu, Z., Wierman, A., Chen, Y. et al. (2013). “Data center demand response.” ACM SIGMETRICS. https://doi.org/10.1145/2465529.2465740

[15] Goiri, I., Le, K., Haque, M. E. et al. (2011). “GreenSlot.” SC Conference. https://doi.org/10.1145/2063384.2063411

[16] Goiri, I., Katsak, W., Le, K. et al. (2013). “Parasol and GreenSwitch.” ASPLOS. https://doi.org/10.1145/2451116.2451123

[17] Qureshi, A., Weber, R., Balakrishnan, H. et al. (2009). “Cutting the electric bill for internet-scale systems.” ACM SIGCOMM. https://doi.org/10.1145/1592568.1592584

[18] Liu, Z., Lin, M., Wierman, A. et al. (2011). “Geographical load balancing with renewables.” ACM SIGMETRICS Performance Evaluation Review. https://doi.org/10.1145/2160803.2160862

[19] Radovanović, A., Koningstein, R., Schneider, I. et al. (2023). “Carbon-Aware Computing for Datacenters.” IEEE Transactions on Power Systems. https://doi.org/10.1109/TPWRS.2022.3173250; https://arxiv.org/abs/2106.11750

[20] Kwag, H.-G. and Kim, J.-O. (2012). “Optimal combined scheduling of generation and demand response with demand resource constraints.” Applied Energy. https://doi.org/10.1016/j.apenergy.2011.12.075

[21] de Chalendar, J. A. and Benson, S. M. (2019). “Why 100% Renewable Energy Is Not Enough.” Joule. https://doi.org/10.1016/j.joule.2019.05.002

[22] Miller, G. J., Novan, K. and Jenn, A. (2022). “Hourly accounting of carbon emissions from electricity consumption.” Environmental Research Letters. https://doi.org/10.1088/1748-9326/ac6147

[23] Riepin, I. and Brown, T. (2024). “On the means, costs, and system-level impacts of 24/7 carbon-free energy procurement.” Energy Strategy Reviews. https://doi.org/10.1016/j.esr.2024.101488; https://arxiv.org/abs/2403.07876

[24] Riepin, I., Jenkins, J. D., Swezey, D. and Brown, T. (2025). “24/7 carbon-free electricity matching accelerates adoption of advanced clean energy technologies.” Joule. https://doi.org/10.1016/j.joule.2024.101808

[25] Riepin, I., Brown, T. and Zavala, V. M. (2025). “Spatio-temporal load shifting for truly clean computing.” Advances in Applied Energy, 17, 100202. https://doi.org/10.1016/j.adapen.2024.100202; https://arxiv.org/abs/2405.00036

[26] Wan, H., Fang, L. and Li, X. (2025/2026). “Grid Operational Benefit Analysis of Data Center Spatial Flexibility: Congestion Relief, Renewable Energy Curtailment Reduction, and Cost Saving.” arXiv preprint arXiv:2511.08759, v1 2025-11-11, v2 2026-03-27. https://arxiv.org/abs/2511.08759

[27] Ma, D., Ye, Y., Wu, Y. et al. (2025). “Bi-Level Optimisation Model for Harvesting Spatial-Temporal Load Shifting Flexibility of Data Centres Using Endogenously Formed Locational Price Signal.” IET Smart Grid, 8(1), e70020. https://doi.org/10.1049/stg2.70020

[28] Lin, L. and Chien, A. A. (2025). “Distribution and Management of Datacenter Load Decoupling.” arXiv preprint arXiv:2511.08936. https://arxiv.org/abs/2511.08936

[29] Zhang, W., Fang, L., Zhao, F. et al. (2025). “Operational risk assessment of power system considering transmission limitation on flexible resources and its application to SCUC.” AIP Advances, 15, 115016. https://doi.org/10.1063/5.0302342

[30] Fan, Y. and Zhao, J. (2026). “Harnessing Flexible Spatial and Temporal Data Center Workloads for Grid Regulation Services.” arXiv preprint arXiv:2602.01508. https://arxiv.org/html/2602.01508

[31] Khanal, S., Roh, G., Yao, B. et al. (2026). “Shift or curtail? How much data-center flexibility is worth depends on the host power grid.” arXiv preprint arXiv:2608.19622. https://arxiv.org/html/2608.19622

## 8 制度与标准资料

- Federal Energy Regulatory Commission (2026). 195 FERC ¶ 61,216; Docket EL26-69-000, Order Instituting Proceeding Under Section 206 of the Federal Power Act. https://www.ferc.gov/sites/default/files/2026-06/EL26-69-000.pdf
- EnergyTag (2024). Granular Certificate Matching Standard, Version 1. https://energytag.org/wp-content/uploads/2024/03/Granular-Certificate-Matching-Standard_V1.pdf
- Google (2021). 24/7 Carbon-Free Energy: Methodologies and Metrics. https://sustainability.google/reports/24x7-carbon-free-energy-methodologies-metrics/
