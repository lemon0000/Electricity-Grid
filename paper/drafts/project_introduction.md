# 电网响应与绿电匹配下智算中心业务柔性的可交付性研究

更新日期：2026-10-21。本文说明当前论文的研究问题、方法和进展。

## 1 这个项目研究什么

本项目研究一个具体问题：智算中心同时承担电网响应和小时级无碳电力（carbon-free energy, CFE）匹配要求时，需要具备多少可实际兑现的业务调节能力？这里的业务调节，是把一部分允许延期的计算任务从当前小时移到之后完成，同时遵守任务截止时间。计算任务可以后移，但没有因此消失；当前减少的用电，会在之后形成恢复计算和用电需求。

例如，一项允许延期的计算可以在电网紧张时暂停，之后再补做。如果补做时段也缺少可匹配的清洁电量，或任务已接近截止时间，原计划就可能无法兑现。这个假设例子说明，本研究需要把降负荷与之后的任务完成放在同一条时间线上考察。

两类要求可能调用同一批可延期任务。电网可能要求某些时段降低负荷，清洁电力不足也可能要求把计算移到其他时段。如果分别规划，两边可能各自认为同一份柔性可以完整使用；即使各自看起来可行，实际共同执行时也可能遇到可延期任务不足、恢复空间不足或截止时间冲突。另一方面，两类服务的时序组合也可能缓解原有瓶颈。因此，研究需要计算联合履约的容量要求，并判断相互影响的方向和大小。

当前论文以这一联合可交付性问题为中心，固定智算中心接入电网的位置。研究关注完整时序中的响应与恢复，并考察当下能减少多少用电，以及之后能否把任务补完。

## 2 基本概念

| 概念 | 本项目中的含义 |
|---|---|
| 业务柔性 | 在任务允许范围内调整计算时间，并按期完成计算的能力。 |
| 电网响应 | 在规定电网约束下，按要求减少智算中心的取电负荷，并检查响应后的电网状态。 |
| 小时级CFE匹配 | 将每小时用电的目标份额，与同小时、适用地域内可归属的无碳发电量进行核算匹配。 |
| 恢复与恢复债务 | 恢复是补做延期任务；恢复债务是尚未完成的计算工作量，需要持续追踪其期限。 |
| 可交付性 | 在声明的模型、服务要求和信息条件下，能否完成调用、通过电网检查并满足任务期限。 |

标题中的“绿电匹配”在模型中采用CFE口径，范围比仅包含可再生能源更广；具体可计入来源由核算边界确定。这种匹配是电量归属核算，不追踪物理电子。例如，某小时用电100MWh，目标为80%，则需要同小时适用范围内80MWh可归属的无碳电量。该例只是说明比例计算，不是本项目的实验结果。实际调节还要考虑延期任务之后能否恢复，以及恢复时是否仍有符合目标的清洁电量余量。


![图1 同一份业务柔性支持两类用电要求](../figures/project_network_cn.svg)

**图1 同一份业务柔性支持两类用电要求。**电网条件和按模型分配的小时级清洁额度共同影响任务安排；两类承诺最终都要在同一套任务、功率和完成期限限制下检查。

## 3 当前论文要回答的三个问题

围绕当前论文，研究分成三个相互衔接的问题。

第一，小时级CFE目标逐步提高时，在既定电网响应要求下，最低业务柔性容量如何变化？希望识别哪些区域可以履约，哪些区域只能确定容量范围，以及哪些区域尚无充分证据。任务可延期比例和恢复空间如何改变这条前沿，也是重要解释变量。

第二，联合承担两类服务，相对于更严格的单项服务，带来多少额外容量要求或组合缓解？进一步，分别规划两类服务，与正确共享物理资源相比，会形成什么方向和大小的容量偏差？研究将通过四种方案的有符号差值进行归因，不预设联合一定更昂贵，也不预设分账一定低估需求。

第三，训练阶段选定的容量与业务策略，在未参与选择的新场景中能否履约？需要分别观察电网响应缺口、CFE缺口、两项要求共同满足的情况，以及延期工作是否按期完成，以判断规划结论的适用范围。

## 4 研究方法与比较方案

### 4.1 连续时序模型

模型以小时为步长，连接电网运行、服务请求、任务延期和业务恢复。主要容量指标为双向业务调节容量D：削减功率q与恢复功率r共享同一个容量上限，满足q+r≤D。与此同时，实际可延期任务量、任务期限、调用持续时间与次数、累计预算和恢复功率余量分别构成约束。恢复能力还受当时业务空闲空间约束；适用CFE要求时，也须具备相应的同小时清洁电量余量。因此，仅有一个MW上限不足以保证完整履约。

每次评估先跟踪连续168小时（一周）内的服务请求及由此推迟的任务；必要时，再观察最多24小时，判断这周内推迟的任务是否按期完成，最大模拟跨度为192小时。模型规定延期工作在产生延期后24小时内完成。跨日持续追踪未完成任务和已使用的调节预算。后续一天产生的新任务也要占用实际资源，但评价对象仍是原来一周内登记的服务与任务。若缺少判断所需的后续输入，相应结局保留未知或右删失，已经观察到的违规仍如实记录。

业务决策只能使用当时已经揭示的信息。对每种方案、每个参数单元，容量成立的要求是存在同一套只使用当时已知信息的调度规则，能够完成预先声明的全部训练场景；不能在事后知道未来后，再为每条场景单独挑选有利动作。

### 4.2 四种比较方案

| 方案 | 用途与处理方式 |
|---|---|
| 仅电网响应（network-only） | 仅承担电网响应，识别网络侧服务的柔性需求。 |
| 仅小时级CFE匹配（CFE-only） | 仅承担小时级CFE要求，识别清洁电量匹配的柔性需求。 |
| 联合承诺与共享资源（joint-correct） | 将两项独立服务承诺相加，在一份可延期任务量、容量、债务和时序预算内履约。 |
| 两项分别计算（joint-B6） | 两项服务分账规划，各自使用完整容量和可用量；实际执行根据共同服务请求和一份当前业务状态重新安排任务，使用一份共享物理资源。 |

联合方案采用“分离承诺相加”的特定比较假设：分别承诺的响应量需要共同兑现，不能在规划账上重复占用资源。这不意味着一切现实共服务都必须把需求相加，也不代表该方案在所有共服务安排中资源最优。分别计算方案用于测量分账规划的偏差。它的实际执行根据共同服务请求和一份当前业务状态重新生成动作，再单独检查服务能否兑现。

### 4.3 场景设计与评价

图中的“容量需求”将画成一条关系曲线：横轴为每小时希望达到的CFE比例，纵轴为满足要求所需的业务调节容量。比较不同任务条件下的曲线，可以判断要求提高后，主要瓶颈来自当期削减还是之后的补做。

研究使用RTS-GMLC电网资料、Alibaba工作负荷资料与Google功率资料。这些来源经过明确假设后构成模型配对，不视为现实中同一地点、同时发生的联合观测。250MW是工作负荷映射的模拟尺度，业务参数也需作为机制假设说明。

当前设计包括9组可延期比例与恢复余量组合，以及10组单因素变化，共19组参数；每组扫描1%至100%的100个小时级CFE目标，合计1,900个单元。这是当前采用的探索性研究设计。计算将区分同一完整合同下的有效容量下界、经完整策略履约验证的上界与未决区域；某个算法或固定策略失败，不等于所有策略都不可能成功。

训练与留出场景严格分开。完成训练证据后冻结容量与策略，再进行留出评价，报告电网、CFE及联合服务缺口和未完成工作。结果解释限于声明的数据支持和机制假设。


![图2 从任务调节到两类服务的研究思路](../figures/project_workflow_cn.svg)

**图2 从任务调节到两类服务的研究思路。**四种方案使用相同的外部场景和相应业务规则。比较容量需求后，再检查选定计划在新场景中能否满足电网、清洁电力和任务完成要求。

## 5 与已有研究的关系

已有研究为本项目提供了三个直接基础。第一，数据中心可以通过调整任务和用电时间参与电力系统运行。需求响应、批作业调度和碳感知计算研究已讨论怎样安排计算，以及功率、持续时间和业务恢复等限制如何影响可调能力[5,7,13–20]。第二，灵活接入与容量规划研究说明，允许负荷在一定条件下调整用电，会影响接入位置、容量和扩建选择[1–3,6]。第三，年度与小时级清洁电力匹配研究说明，清洁电力目标的时间粒度会改变采购和任务调度安排[21–25]。

与本项目最接近的工作还包括网络拥塞与新能源利用的联合调度、服务承诺及可交付性研究[4,26–31]。其中，Fan和Zhao[30]已经把工作负荷安排与电网服务容量承诺联系起来；Khanal等[31]已经在容量扩展中考虑柔性服务的持续时间、恢复和年度上限。因此，本项目的研究重点放在更具体的问题上：固定电网响应规则后，逐步提高小时级CFE目标，所需业务柔性如何变化；单项服务瓶颈、共同执行的时序影响及分开计算的偏差各占多少；选定计划在新场景中能否兑现。

FERC网络服务文件，以及EnergyTag和Google的小时级核算方法，分别支撑两类制度要求的存在。将两类要求落实到现实中同一套合同、同一计量边界和同一批任务，还需要直接证据。本项目据此开展具名规则下的机制研究，结果解释保留这一条件。输电扩展与鲁棒规划研究[8–12]补充了相关电网规划方法。

![图3 相关研究与本项目的问题定位](../figures/project_literature_landscape_cn.svg)

**图3 相关研究与本项目的问题定位。**上部整理本文审阅的31篇学术文献，下部展示主题分组及本项目如何连接两类服务要求。图中的主题分组用于说明研究关系；示意带宽度不代表文献数量或证据强弱。

## 6 目前做到哪一步

截至2026年10月21日，项目已形成规划与任务时移的模型基础，并有选定设备故障下的直流电网运行计算基准。逐小时联动流程已完成首小时及两小时、三小时合成用例，覆盖部分事故延续、修复、恢复债务和分支未决情形；保存结果关闭后重新打开的重放核验也已完成。这些例子用于检查流程是否按预定规则运行，属于合成开发验证，尚不提供正式容量或服务风险结论。

完整168小时登记及按需最多24小时后续观察的连续执行、生产资源预算、正式容量前沿和固定策略留出结果仍未完成。10月21日的工作重点是分析重复来源检查与历史重放的成本，为完整流程优化提供依据。目前没有完整192小时的实测运行时间，也尚不能给出正式容量或服务风险结论。

## 7 预期成果与研究范围

预期成果包括小时级CFE目标与最低柔性容量的关系、四方案有符号归因、固定策略在新场景中的履约后果，以及能够追溯输入、状态延续和恢复结局的计算记录。研究希望说明在什么条件下业务柔性足以支撑双重要求，以及哪些任务和时序约束构成主要瓶颈。

接下来的工作依次推进：先核验计算流程与重复检查的复用方式，核定整套计算的资源预算；在此基础上开展一周运行及后续任务恢复的连续验证，确认跨日任务和缺失数据处理正确；随后按当前参数设计计算容量需求及可信范围；最后固定训练阶段选定的计划，用新场景评价两类服务和任务完成情况。

研究结论适用于声明的任务规则、数据情景和电网检查范围。若只能证明容量处于某个区间，就报告区间；若缺少判断所需的数据或计算证据，就保留未知。模型中的可交付性是这些明确条件下的履约能力。工程安全还需要完整的设备故障范围、交流潮流以及设备与控制检查。

## 8 参考文献

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

## 9 制度与标准资料

- Federal Energy Regulatory Commission (2026). 195 FERC ¶ 61,216; Docket EL26-69-000, Order Instituting Proceeding Under Section 206 of the Federal Power Act. https://www.ferc.gov/sites/default/files/2026-06/EL26-69-000.pdf
- EnergyTag (2024). Granular Certificate Matching Standard, Version 1. https://energytag.org/wp-content/uploads/2024/03/Granular-Certificate-Matching-Standard_V1.pdf
- Google (2021). 24/7 Carbon-Free Energy: Methodologies and Metrics. https://sustainability.google/reports/24x7-carbon-free-energy-methodologies-metrics/

## 10 设计与进度依据

- [科研范围与首篇定位](../../agent.md)：当前研究范围及证据边界；
- [finite-v2参数合同](../../configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml)与[模型规格](../../docs/model_spec/rq2_finite_mechanism_protocol_candidate_v2.md)：168h、24h、q+r≤D、1,900 cells及开发授权；
- [执行计划](../../docs/plan/科研项目执行步骤.md)与[blocker register](../../docs/model_spec/blocker_register.md)：阶段证据、开放问题和解除条件；
- [H1端到端里程碑](../../docs/plan/H1_端到端里程碑验收_v1.md)：完整hour-0至正式运行的验收顺序；
- [chain_07保存计时](../../results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/chain_07/timing.jsonl)与[来源边界检查](../../results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/source_boundary_status_rechecked_01.json)：开发进度与获批来源覆盖；
- [hour-0完整报告](../../results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/chain_07/complete_integration_report_supplement_04.md)及[独立后验04](../../results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/chain_07/postcheck_supplement_completion_04.json)：首小时合成链和独立进程保存重放；
- [两小时批量重放验收](../../results/tables/rq2_h1_cross_hour_batch_v2_non_authoritative/acceptance_report.md)及[机器补验](../../results/tables/rq2_h1_cross_hour_batch_v2_non_authoritative/connected_01_postcheck.json)：6个成对lane-hour及保存状态对照；
- [三小时事故与修复验收](../../results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/acceptance_report.md)及[机器补验](../../results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03_postcheck.json)：7个成对lane-hour、分支停止、缺输入与同进程只读重开；
- [B0-B2结果](../../results/tables/rts24_b0_b2_summary.json)、[B3-B5结果](../../results/tables/rts24_b3_b5_summary.json)及[24小时DC benchmark](../../results/tables/rts_gmlc_google_day0_full24h_selected_n1_dc_scuc_v1/summary.json)：既有电网与规划计算的原始证据。


### 容量指标的补充说明

文中四方案对应的容量分别为D_N（仅电网）、D_C（仅CFE）、D_J（联合共享）和D_B（分别计算）。先以两个单项需求中的较大值作为比较基准，再比较联合方案与分别计算方案。相应分解为\(I_{joint}=D_J-\max(D_N,D_C)=I_{sep}+A_{B6}\)，其中\(I_{sep}=D_B-\max(D_N,D_C)\)，\(A_{B6}=D_J-D_B\)。正负方向由容量证据决定。

当前实验设计包含19组任务参数和100个小时级CFE目标，共1,900个参数单元。具体参数、数据范围和原始计算记录见上述依据文件。
