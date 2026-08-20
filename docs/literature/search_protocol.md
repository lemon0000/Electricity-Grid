# 文献检索与编码协议

更新日期：2026-07-13

## 当前状态

本轮建立的是面向模型规格的核心文献矩阵，目标是验证创新边界并找出最近的直接竞争工作，不是投稿前的PRISMA式系统综述。矩阵后续应持续扩展，但任何新增文献都必须落入既定字段，不能只加入书目信息而不编码与三个RQ的关系。

## 检索方向

1. 数据中心灵活接入、firm/flexible容量、non-firm connection和planner-initiated siting。
2. 大型负荷接入、输电/主变扩建及工程工期。
3. 多阶段随机或鲁棒输电扩展、场景树和非预见性。
4. 持续时间受限的需求响应、事件次数、能量约束、恢复和反弹。
5. 数据中心作业暂停、延期、功率限制、碳感知和时空移峰。
6. 年度绿电匹配、小时核算、24/7 CFE和电网可交付性。

本轮使用的查询词簇包括：

- `data center flexible interconnection firm capacity grid`
- `large load interconnection transmission planning data center`
- `multistage stochastic transmission expansion planning uncertainty nonanticipativity`
- `demand response duration recovery rebound energy constraints`
- `data center workload shifting renewable energy grid flexibility`
- `24/7 carbon-free electricity hourly matching annual matching`

## 来源与核验顺序

1. DOI通过Crossref逐条核验正式题名、作者、年份和来源。
2. arXiv条目通过官方Atom API核验题名、作者、日期和摘要。
3. 可用时读取arXiv HTML全文，并用Pandoc转换后筛选模型、约束和算例信息。
4. 生物医学索引覆盖的跨学科论文使用Europe PMC补充摘要。
5. IEA、NERC和DOE报告只使用机构官网或OSTI官方页面。
6. 搜索结果页只用于定位官方来源，不作为文献事实的最终证据。

## 纳入规则

- 至少直接覆盖六个方向之一，并能影响一个RQ、模型约束、实验基线或参数范围。
- 直接竞争文献优先于泛化背景文献；同一工作会议版和期刊版原则上只保留信息更完整的一版。
- 同行评议论文、预印本和机构报告分开标注，不把机构观点等同于同行评议证据。
- 2026年预印本可以用于界定最新竞争边界，但论文写作时必须重新检查版本、发表状态和引用信息。
- 仅讨论市场、电价、跨数据中心迁移或储能属性且不能服务三个RQ的工作，不进入核心矩阵。

## 核验层级

- `F-全文筛选`：已读取可访问全文或等价的完整HTML，并据此编码模型和算例字段。
- `A-摘要筛选`：已核验元数据并读取摘要；摘要没有报告的字段必须写“摘要未报告”，不能推断为“否”。
- `M-元数据核验`：只核验题名、作者、年份、来源和标识符；模型字段一律标记“待全文核验”。

从 `M` 或 `A` 升级为 `F` 时，应复核以下字段：不确定性、决策变量、N-1、工程工期/延期、柔性包络、绿电口径、测试系统，以及与本项目的直接差异。

## 编码规则

- `否` 只用于全文中能够确认没有该机制的情形；证据不足时写“待全文核验”或“摘要未报告”。
- N-1必须区分硬热限额、罚函数软约束、概率门槛和CVaR放松，不能统一写成“考虑安全”。
- “多阶段”必须区分场景树上的序贯规划决策和“一次投资 + 多时段运行”。
- “小时级”必须记录模型实际时间分辨率；例如Riepin and Brown (2024)讨论24/7 CFE，但算例使用2920个三小时快照。
- “绿电”必须区分现场新能源利用、碳强度感知、年度证书匹配和同小时可归属CFE。
- 数据中心柔性必须区分永久放弃、延期完成、跨地点迁移和事故削减，并记录是否有能量守恒或恢复状态。
- 与项目的差异必须写成可验证的模型或实验差异，不能使用“研究较少”“尚不充分”等空泛表述。

## 已发现的书目信息修正

| 计划文档中的写法 | 核验结果 | 处理 |
|---|---|---|
| `arXiv:2605.18517` 写作 *Data Center Spatio-Temporal Renewable Energy Balancing Under Transmission Constraints* | 官方题名为 *Data Center Spatio-Temporal Load Flexibility in Security-Constrained Unit Commitment for Enhanced Grid Efficiency and Reliability* | 矩阵和最新计划文档均已同步更正 |
| `arXiv:2606.25098` 写作 *Power-Flexible AI Data Centers: A Comprehensive Survey of Grid Integration, Modeling, and Control* | 官方题名为 *Power-Flexible AI Data Centers: A New Paradigm for Grid-Responsive Compute* | 矩阵和最新计划文档均已同步更正；该文是实证/架构论文，不按综合综述编码 |
| Nature Communications条目的作者缩写和题名大小写不统一 | DOI `10.1038/s41467-026-72324-9` 已由Crossref和Europe PMC核验 | 采用Crossref正式题名和完整作者名 |

## 2026-08-20 RQ2查新增补记录

围绕RQ2护城河做定向查新，新增四条并全部核验官方元数据：

| id | 标识符 | 核验来源 | 层级 | 纳入理由 |
|---|---|---|---|---|
| DC11 | arXiv:2511.08759（v1 2025-11-11，v2 2026-03-27，eess.SY） | arXiv官方页 | F | IEEE 73-bus OPF、单一空间负荷重分配变量联合缓解拥塞与弃光，是RQ2最近邻直接竞争，用于界定“统一变量天然不重复”反驳 |
| DC12 | DOI 10.1049/stg2.70020（IET Smart Grid Vol 8 Issue 1 e70020, 2025） | 出版社官方页 | F | IEEE 39-node双层内生LMP驱动时空移峰，代表价格信号一体化目标路线，非分离合同承诺 |
| DC13 | arXiv:2511.08936（2025-11-12，cs.DC） | arXiv官方页 | F | 数据中心负荷解耦碳收益，系统级、无输电N-1，界定研究边界 |
| FLEX09 | DOI 10.1063/5.0302342（AIP Advances Vol 15, 115016, 2025） | 出版社官方页 | F | 两阶段随机鲁棒SCUC下传输受限对（发电侧）柔性资源可用性的运行风险，支持RQ2场景外履约风险动机，非数据中心接入模型 |

排除说明：本轮同时检出但未纳入核心矩阵的相邻工作包括Ren et al. (2025, arXiv:2510.01050，数据中心频率响应Safe-UC)与若干配网拥塞市场/碳责任分摊文，因其目标为频率安全或市场机制、不服务RQ2重复承诺证据链，仅在下一轮按需追踪。

## 下一轮全文队列

最高优先级：

1. Han et al. (2020) 与 Webster (2022)：核验场景树、非预见性、扩建阶段和安全约束。
2. Jabr (2013) 与 Li et al. (2021)：核验鲁棒扩展、active load和N-1处理。
3. Riepin et al. (2025)：核验24/7 CFE约束、技术组合和网络表示。
4. NERC (2025) 与 IEA (2025)：编码大型负荷行为、可靠性风险和数据中心增长参数。
5. Kwag and Kim (2012)、GreenSlot及Parasol/GreenSwitch：核验持续时间、能量守恒和恢复含义。

## 文献阶段停止条件

在进入论文结果固定阶段前，以下条件必须同时满足：

- 三个RQ各至少有两篇全文级直接竞争或方法文献。
- 所有声称“现有工作未包含”的关键字段均来自全文证据，而不是摘要缺失。
- 对核心文献完成前向和后向引文追踪，并记录新增条目为何纳入或排除。
- 2026年预印本的版本和发表状态重新核验。
- Introduction中的每一项相关工作判断都能回到矩阵中的一行和一个证据层级。
