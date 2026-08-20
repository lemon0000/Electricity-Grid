# 研究缺口与贡献定位（第一版）

更新日期：2026-07-13；2026-08-20补充RQ2最近邻文献查新  
适用范围：当前核心文献筛选，不等同于投稿前的穷尽式系统综述

> 2026-08-20查新说明：为核实RQ2护城河，补入四篇2025-2026直接相关工作——Wan, Fang and Li (2026, DC11)、Ma et al. (2025, DC12)、Lin and Chien (2025, DC13)与Zhang et al. (2025, FLEX09)。四篇均已全文/官方元数据核验并编码入`literature_matrix.csv`。结论不变：这些工作分别在单一统一调度变量下联合拥塞与消纳、或做碳导向解耦、或做运行层传输受限风险，均未把网络条件服务与小时级CFE建成两项分开签约的独立合同承诺，也未构造重复承诺错误基线并量化场景外履约风险。RQ2仍是可检验空白。

## 一页结论

截至当前筛选范围，相关研究已经分别覆盖数据中心可中断或可移峰运行、firm/flexible容量、数据中心选址与容量扩展、多阶段随机输电扩展、N-1安全约束运行，以及年度与24/7 CFE采购。因此，本项目不能把任何单一模块宣称为创新。仍然存在的可检验缺口是：对于一个固定接入点的大型AI智算中心，当业务达产和电网工程进度在季度节点逐步揭示时，现有直接竞争模型尚未同时给出满足非预见性的F/X序贯释放和未开工扩建调整策略；现有网络灵活性与绿电调度研究也尚未量化两类合同服务重复占用同一业务柔性所导致的条件容量高估及场景外履约风险；已有年度与小时级CFE研究则主要优化清洁发电、储能和采购组合，尚未回答时间粒度变化何时会反向改变固定POI的接入容量释放与电网扩建时序。该缺口是一组模型要素和证据链的特定交叉，不是“首次使用F/X、多阶段随机规划、N-1、CVaR或小时级CFE”。

## 三条证据链

| RQ | 最接近的已有工作 | 已经解决的内容 | 本项目仍需证明的内容 |
|---|---|---|---|
| RQ1 多阶段适应性 | Kim et al. (2026)；Chen and Zheng (2026)；Li et al. (2026)；Han et al. (2020) | 静态运行包络和选址；一次投资加小时调度；静态风险化F/X容量；通用多阶段随机输电扩展 | 固定POI下，需求达产与工程延期按季度揭示时，F/X和未开工工程满足非预见性的序贯策略；在同一外样本上识别其相对静态和两阶段方案的有效与失效区域 |
| RQ2 重复承诺风险 | Wan and Li (2026, DC04)；Wan, Fang and Li (2026, DC11)；Ma et al. (2025, DC12)；Williams et al. (2026)；Radovanović et al. (2023)；Zhang et al. (2025, FLEX09) | 单一统一变量内联合时空移峰、拥塞缓解和新能源消纳；价格信号驱动的时空移峰；实证AI集群可快速持续削减；碳感知调度；运行层传输受限对柔性可用性的风险 | 将网络条件服务与CFE移峰表示为**分开签约、分开触发**的两个可审计承诺并共享同一业务时序包络；设置允许重复承诺的B6错误基线，在场景外执行既定策略，量化X高估、持续时间违约、恢复债务和失败概率 |
| RQ3 绿电时间粒度 | de Chalendar and Benson (2019)；Miller et al. (2022)；Riepin and Brown (2024)；Riepin et al. (2025) | 年度核算的时间错配；年度与小时核算偏差；年度与24/7 CFE对发电、储能、成本和技术选择的影响 | 在固定POI、N-1和扩建工期约束下，年度与小时级属地CFE是否改变F/X轨迹、T20/T50/T100、扩建启动/投运时序，以及网络服务与绿电服务之间的柔性分配 |

## 缺口边界

### 1. 不是“有没有多阶段模型”，而是信息结构是否对应真实双重时钟

多阶段随机输电扩展已经存在，数据中心容量扩展也已有两阶段模型。现有直接竞争工作通常采用静态包络、静态风险容量，或“一次投资 + 小时运行”的两阶段结构。项目的主张必须收窄为：季度节点只使用已经观察到的机柜/客户激活和工程进度信息，并允许调整后续F/X释放与尚未开工的工程，同时用非预见性测试排除未来信息泄漏。

RQ1只有在相同安全标准、相同训练场景和相同外样本上比较B2静态F/X、B3两阶段和B4多阶段后才成立。VMA接近零、静态方法占优或多阶段方法只在极端调参下占优，都是需要报告的结果。

### 2. 不是“首次联合新能源和负荷灵活性”，而是合同资源是否被重复占用

多篇近期直接竞争工作已在**单一统一调度变量**下同时缓解拥塞并消纳新能源，因此不能声称首次联合网络与新能源目标：

- Wan and Li (2026, DC04)在修改RTS-24的SCUC中用同一负荷灵活性变量联合服务系统目标（软罚拥塞与弃光），并考虑37线N-1；
- Wan, Fang and Li (2026, DC11)在IEEE 73-bus的OPF上用单一跨节点空间负荷重分配变量把拥塞越限降30.1%、弃光降61.0%；
- Ma et al. (2025, DC12)在IEEE 39-node上用内生LMP价格信号驱动数据中心时空移峰，把可再生消纳提升26.6%、降碳63%。

这些工作的共同特征是：**用一个变量表示同一时刻的物理负荷再分配，因而在结构上天然不会重复计数**。它们既没有把“网络条件服务”和“小时级CFE移峰”表示为两项**分开签约、分开触发**的独立合同承诺，也没有构造允许重复承诺的错误基线并在独立场景中执行既定策略。Lin and Chien (2025, DC13)与Zhang et al. (2025, FLEX09)进一步说明相邻方向的边界：前者只做碳收益导向的负荷解耦、无输电N-1；后者只在运行层评估传输受限对（发电侧）柔性资源可用性的影响，二者都不涉及数据中心F/X接入分层与多服务重复承诺。

因此必须正面预答审稿人最可能的反驳——“既然统一建模就不会重复，为什么还要研究重复承诺？”。答案是：现实中两类服务的**契约与触发机制是分离的**——网络条件削减是对N-1事件的被动、事后响应，小时级CFE移峰是跟随绿电的主动、事前调度；二者由不同合同、不同时间尺度触发，却抽取自**同一业务柔性物理包络**（同一MW上限、同一持续时间与恢复债务预算）。当规划者把两份合同分别按各自“可用灵活性”签出条件容量X时，就会在时序上重复占用同一物理包络。真正的冲突不仅在MW上限，更在于持续时间与恢复债务等**时序维度**：即便瞬时MW不冲突，两类服务在同一压力窗口内的累计调用、事件次数与恢复功率也可能同时突破物理上限。

因此，RQ2的贡献不是单独写出 `c_grid + c_green <= D_flex` 这一条不等式，而是三个维度的组合：（i）机制创新——建立可执行的**共享时序包络**（MW、持续时间、事件次数、累计能量、恢复功率和恢复债务），把上述“契约分离但物理共享”结构显式化；（ii）概念创新——设置允许重复承诺的B6错误基线，将“忽略共享包络”这一被现有统一变量模型隐式规避、却在分离签约现实中真实存在的错误显式化并可证伪；（iii）评估创新——在训练集外独立场景上执行既定策略，量化X高估幅度、持续时间违约、恢复债务累积和场景外失败概率，并对 $\kappa/\lambda/\beta$ 系数做敏感性以证明合成参数下结论的稳健性。

### 3. 不是“首次比较年度和小时级CFE”，而是时间粒度是否改变接入与扩建

Riepin and Brown (2024)已经直接比较年度匹配与24/7 CFE，并联合优化发电、储能和网络运行；Riepin et al. (2025)进一步讨论先进清洁技术采用。因此，年度/小时比较本身不能作为创新。

本项目需要把问题落到接入规划：当清洁电量必须与数据中心同小时、属地且网络同时可行时，约束是否改变F/X容量释放、扩建启动和柔性分配，而不仅仅提高成本或改变清洁技术组合。`y_CFE`只能解释为同小时可归属清洁电量，不能解释为电子物理来源追踪。

## 可用于 Introduction 的贡献定位

现有研究分别表明，数据中心的可中断和时空移峰能力能够扩大接入可行域、缓解网络拥塞并改善清洁能源利用，多阶段随机规划也能够处理长期电网扩展不确定性。然而，已有数据中心接入模型主要采用静态运行包络、静态风险容量或一次投资后的小时级补救，尚未刻画业务达产与工程进度逐季揭示时的F/X容量释放和扩建调整；与此同时，年度与24/7清洁电力采购研究通常将负荷侧灵活性用于能源匹配，而未检验该灵活性与网络条件服务之间的合同资源冲突。为此，本文构建固定接入点下满足非预见性的多阶段F/X接入与扩建模型，并以统一的业务灵活性包络约束网络削减和小时级CFE移峰。通过静态、两阶段、多阶段及允许重复承诺的错误基线，本文在独立场景中识别多阶段适应性的有效区域、重复承诺造成的容量高估与履约风险，以及年度和小时级CFE对接入容量和扩建时序的差异化影响。

英文工作稿：

> Existing studies show that interruptible and spatiotemporally shiftable data-center loads can expand interconnection feasibility, relieve network congestion, and improve clean-energy utilization, while multistage stochastic planning can address uncertainty in long-term grid expansion. Yet data-center interconnection models largely rely on static operating envelopes, static risk-based capacity allocations, or hourly recourse following a one-time investment decision; they do not represent sequential releases of firm and conditional capacity as data-center ramp-up and project delays are progressively observed. In parallel, annual and 24/7 clean-energy procurement studies optimize energy matching without testing whether the same workload flexibility has also been contractually reserved for network-contingent service. We therefore develop a nonanticipative multistage model for phased F/X interconnection and grid expansion at a fixed point of interconnection, coupled with a shared workload-flexibility envelope for network curtailment and hourly CFE shifting. Out-of-sample comparisons against static, two-stage, perfect-information, and double-counting baselines identify when multistage adaptation is valuable, how much duplicate flexibility commitments overstate conditional capacity and delivery performance, and when annual versus hourly CFE requirements change interconnection and expansion decisions.

## 不能宣称的创新

- 不能宣称首次提出数据中心灵活接入、firm/flexible容量、non-firm connection或connect-and-manage。
- 不能宣称首次把数据中心工作负载用于需求响应、拥塞缓解、跟随新能源或碳感知调度。
- 不能宣称首次建立数据中心容量扩展模型或首次比较时移与跨地域转移。
- 不能宣称首次使用多阶段随机输电扩展、鲁棒规划、CVaR、N-1或场景约简。
- 不能宣称首次联合数据中心灵活性、网络安全与新能源消纳；已有SCUC工作覆盖该组合。
- 不能宣称首次比较年度清洁电力匹配与24/7 CFE，或首次发现年度核算存在时间错配。
- 不能把共享预算的一条不等式单独包装成方法创新；创新证据必须来自错误基线、完整包络和场景外风险量化。
- 不能声称 `y_CFE` 追踪了流向数据中心的清洁电力电子，也不能把同小时可归属等同于物理溯源。
- 不能仅凭合成系统形成某一国家的合同、市场或政策结论。
- 不能预设多阶段方法必然优于静态方法，也不能隐去VMA接近零或为负的区域。

## 进入模型规格阶段前的结论

当前证据足以把项目贡献表述为“特定交叉问题和证据链”，而无需使用上述禁止表述。模型规格阶段必须据此保留以下可证伪设计：

1. 静态F/X、两阶段和多阶段使用同一信息、场景和安全标准。
2. 所有关键N-1热限额为硬约束；CVaR只度量服务或业务损失。
3. 网络服务和CFE服务既要有统一物理预算，也要保留允许重复承诺的错误基线。
4. 年度与小时级CFE实验除时间粒度外保持数据和目标口径可比。
5. 场景外评估执行已经得到的策略，不允许用完整未来信息重新优化规划决策。
