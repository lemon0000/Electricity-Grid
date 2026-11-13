# 数据中心达产阶段与业务柔性耦合：实证数据源与参数映射手册

本手册直接针对 `stage_physical_reduction_v1_findings.md` 中指出的核心缺口（**“缺的不是模型，是数据；需要一份有实证来源的电网—任务联系，证明标准时变容量调度漏掉了什么”**），汇总了已公开发布的超大规模生产集群真实轨迹、GPU 硬件级电网响应实测、PJM 变电站分期达产 SCADA 研究、以及欧美电网柔性并网协议（FCA）的实证参数、开源仓库地址及与你现有代码变量的精确映射关系。

## 1. 可直接下载的四大开源实证数据集与代码仓库

| 数据集 / 仓库名称 | 发布机构与发表年份 | 数据规模与核心内容 | 开源下载链接（Zenodo / GitHub） | 论文原文链接 | 
| ----- | ----- | ----- | ----- | ----- | 
| **Alibaba 15.5万卡生产集群电力轨迹与持久性包络 (`asi-trace-power` v1.0.1)** | 路易斯安那州立大学 (LSU) & 阿里云 (ACM e-Energy '27) | **155,410 块 GPU**（37,707 台服务器、17 个集群），连续 **185 天（4,439 小时）** 的生产轨迹（858,816 行充分统计量表），含训练、在线/离线推理分层功率、待机底噪、任务排队延迟及 **持续时长—可靠性曲面** $K_{\alpha,h}$ | • [Zenodo 完整数据包 (10.5281/zenodo.22308423)](https://doi.org/10.5281/zenodo.22308423)  • [GitHub 代码与结果表 (`meiyilutaustin/asi-trace-power`)](https://github.com/meiyilutaustin/asi-trace-power) | [arXiv:2609.05406v1](https://arxiv.org/html/2609.05406v1) | 
| **PJM 与韩国电网分层数据中心柔性规划数据集 (`Tiered-DC-CEM`)** | 约翰霍普金斯大学 (JHU) & 韩国能源工科大学 (KENTECH) & KAUST (2026) | 包含 PJM 21 分区与韩国 KPG-193 节点的 **Firm / Flexible / Interruptible 三层负荷比例**、24 小时滚动积压账本（Backlog）以及 **Layer B/C 事件包络参数（C1\~C5）** 与 Gurobi/JuMP 源码 | • [Zenodo 模型输入与结果表 (10.5281/zenodo.22016953)](https://doi.org/10.5281/zenodo.22016953) | [arXiv:2608.19622v1](https://arxiv.org/html/2608.19622v1) | 
| **ICARUS 数据中心与 PJM 节点数据集 (`ICARUS-DC` & `ICARUS-PJM`)** | 约翰霍普金斯大学 ICARUS 实验室 (Reed et al. / Khanal et al., 2025) | 美国 PJM 区域真实数据中心空间分布、容量爬坡、开发年份特征及节点电网拓扑映射（CC BY 4.0 许可） | • [ICARUS-DC GitHub 仓库](https://github.com/hopkinsicarus/ICARUS-DC-Dataset)  • [ICARUS-PJM GitHub 仓库](https://github.com/HopkinsICARUS/ICARUS-PJM-Dataset) | [arXiv:2608.19622v1](https://arxiv.org/html/2608.19622v1) | 
| **生成式 AI 全站功率实测集 (NREL / Vercellino et al., 2026)** | 美国国家可再生能源实验室 (NREL) (2026) | 5 秒级高分辨率单节点/集群训练与推理（含 LoRA、Diffusion、Online/Offline Inference）功率实测曲线，用于校验 1 分钟、5 分钟、15 分钟结算窗口下的功率下界 | • [DOE Data Explorer / DOI: 10.7799/3025227](https://arxiv.org/html/2609.05406v1) | [arXiv:2604.07345](https://arxiv.org/html/2609.05406v1) | 

## 2. 核心实证证据：为什么“逐小时标量容量 $C_t$”在真实数据下必然失效？

你在 `stage_physical_reduction_v1_findings.md` 中证明了仿射功率映射 $P_t = b + a x_t$ 在外生给定标量供电上限时可精确压缩为 $0 \le x_t \le C_t$。而 [**Li et al. (2026, arXiv:2609.05406v1)**](https://arxiv.org/html/2609.05406v1) 基于阿里云 155,410 块 GPU 的 4,439 小时生产数据，恰好从实证角度直接证伪了“标量容量/固定百分比（Scalar Flexibility）”假设，提供了三个可直接写入你论文的核心定理级实证事实：

### 2.1 持续时长衰减曲面 $K_{\alpha,h}$（打破逐小时独立投影）

在生产集群中，即使低优先级可抢占任务（Eligible-attributed）占工作负载功率的 **20.39%（5.99 MW）**，由于被抢占的 GPU 仍保持分配状态并消耗 **20% TDP 的待机底噪（2.44 MW）**，瞬时可削减的净有功功率（Idle-retained relief）仅为 **3.55 MW**（占工作负载功率的 **12.08%**，占全站中位功率 **55.83 MW** 的 **6.35%**）。

更重要的是，当电网要求连续削减 $h$ 小时且满足 95% 可靠性（$\alpha = 0.95$）时，13 个集群组合的**可靠可削减容量** $K_{0.95,h}$ **随持续时间** $h$ **显著衰减**（见 [arXiv:2609.05406v1 Table 2 & Table 3](https://arxiv.org/html/2609.05406v1)）：

| 电网调用持续时长 $h$ | 95%可靠实测可削减功率 $K_{0.95,h}$ (MW) | 容量坚实度 (Firmness = $K_{0.95,h}/\bar{C}$) | 等效工作负载可削减比例乘子 $p_{h,0.95}$ | 均值标量模型 ($C_t$ Scalar) 高估误差 | 4小时尾部标定标量模型误差 | 独立集群假设 (忽略跨集群协方差) 高估误差 | 
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | 
| **1 小时** | **2.508 MW** | **0.710** | **0.85** $\times \bar{p}$ | **+17.4%** (比值 1.174) | **-6.4%** (比值 0.936) | **+7.3%** (比值 1.073) | 
| **2 小时** | **2.420 MW** | **0.686** | **0.83** $\times \bar{p}$ | — | — | — | 
| **4 小时** | **2.317 MW** | **0.656** | **0.79** $\times \bar{p}$ | **+25.5%** (比值 1.255) | **0.0%** (基准点 1.000) | **+11.0%** (比值 1.110) | 
| **8 小时** | **2.160 MW** | **0.612** | **0.74** $\times \bar{p}$ | — | — | — | 
| **24 小时** | **1.947 MW** | **0.551** | **0.68** $\times \bar{p}$ | **+46.6%** (比值 1.466) | **+16.9%** (比值 1.169) | **+19.7%** (比值 1.197) | 

* **科研结论支撑**：[arXiv:2609.05406v1](https://arxiv.org/html/2609.05406v1) 明确证明，任何标量容量模型（无论按均值标定还是按 4 小时尾部标定）都无法同时对齐 1 小时、4 小时和 24 小时的可行域边界（标量高估达 **17.4% \~ 46.6%**；若采用 [Duke 研究](https://nicholasinstitute.duke.edu/sites/default/files/publications/rethinking-load-growth.pdf) 的 100% 或 20% 全站削减假设，则高估达 **19.0 倍** 和 **3.8 倍**）。

### 2.2 Checkpointing 回滚损耗与“负节能（Rebound Debt Expansion）”实证公式

在你现有的模型中，$x_t = w_t - q_t + r_t$，且债务账本满足 $\text{debt}/\eta$。在 [arXiv:2609.05406v1 Section 3.6 & Appendix D](https://arxiv.org/html/2609.05406v1) 中，给出了具有严格物理实证的 **Checkpointing 算力回滚与能量反弹公式**：

* 设电网调用持续时长为 $h$ 小时，任务反弹系数为 $\rho \in [0, 1]$（对于不可丢弃的训练/批处理任务 $\rho = 1$），检查点保存间隔为 $T_{\text{ckpt}}$ 小时（实证基准取 $T_{\text{ckpt}} = 1.0\text{ h}$）。

* 当调用发生且任务被抢占时，平均损失半个检查点周期的已执行算力 $T_{\text{ckpt}} / 2 = 0.5\text{ h}$。因此，调用结束后需要偿还的反弹能量债务（Rebound Energy Debt）与总削减能量之比为：
  

  $$
  \frac{E_{\text{rebound}}}{E_{\text{curtailed}}} = \rho \left(1 + \frac{T_{\text{ckpt}}}{2h}\right), \quad \text{净节能量比例} = 1 - \rho \left(1 + \frac{T_{\text{ckpt}}}{2h}\right)
  $$

* **实证数值（4 小时调用基准）**：当 $h = 4\text{ h}, \rho = 1, T_{\text{ckpt}} = 1\text{ h}$ 时，净节能量比例为 $-12.5\%$！即削减 $2.32\text{ MW} \times 4\text{ h} = 9.28\text{ MWh}$ 的负荷，会在恢复期产生 $10.44\text{ MWh}$ 的反弹算力债务（相当于你代码中的恢复效率因子 $\eta = \frac{1}{1 + T_{\text{ckpt}}/(2h)} = \frac{1}{1.125} = 0.8889$，且**随调用持续时长** $h$ **动态变化**，短调用 $h=1\text{ h}$ 时 $\eta = 1/1.5 = 0.6667$，损耗高达 50%！）。

* **恢复期吸收上限与最小调用间隔**：在生产轨迹中，非弹性基荷与平移层（Floor + Shift）均值为 $23.264\text{ MW}$。若恢复期仅允许以该基荷的 **10%（即** $r_{\max} = 2.326\text{ MW}$**）** 吸收反弹债务，偿还 $10.44\text{ MWh}$ 债务需要 $4.49\text{ 小时}$，从而在物理上强制要求两次 4 小时电网调用之间的最小周期不低于 $8.49\text{ 小时}$（每周最多调用 $19.8$ 次）。

### 2.3 硬件级实测：15 分钟优雅爬坡（Graceful Ramp）与 SLA 延迟边界

根据 [**Williams et al. (2026, arXiv:2606.25098v1)**](https://arxiv.org/html/2606.25098v1)（由 Emerald AI、EPRI、英国国家电网 National Grid、NVIDIA 和 Oracle 联合在伦敦 130 kW 96卡 Blackwell Ultra 集群及美国弗吉尼亚/芝加哥 60 kW 80卡 H100 集群上开展的真实电网调度实验）以及 [**Phoenix AI Factory 256卡试点**](https://impacteci.substack.com/p/data-center-flexibility-chapter-2)：

* **零通知紧急调用（Emergency Dispatch）**：面对模拟 2019 年英国电网雷击切机事故的零预警指令，集群可在 **40 秒内削减 30% 功率**，或在 **60 秒内削减 40% 功率**。

* **计划/常规调度爬坡（Graceful Ramp）**：为保护训练状态与推理 SLA，集群执行 **15 分钟平滑降载（Ramp-down）** 和 **15 分钟平滑升载（Ramp-up）**，将 H100 功率上限锁在 **375 W** 并维持 **3 小时**（在伦敦测试中持续削减 **10%\~40%** 达 **2\~10 小时**，跨越 200+ 次 National Grid 调度事件实现 100% 合规）。

* **对在线推理 SLA 的真实冲击**：当弗吉尼亚 Ashburn 集群限电并向芝加哥集群转移 10% 流量时，受限集群的平均首字延迟（**Time to First Token, TTFT**）出现约 **+30 ms** 的持续上升。

* **EPRI DCFlex 四级任务 SLA 容忍度（[ImpactECI / EPRI DCFlex](https://impacteci.substack.com/p/data-center-flexibility-chapter-2)）**：

  * **Flex 0**：严苛 SLA（在线核心推理），允许降级 **0%**（对应 [arXiv:2609.05406v1](https://arxiv.org/html/2609.05406v1) 中占 IT 功率 **46.12%** 的 Floor 层，且在线推理即使在极低 SM 利用率下仍有 **0.43 TDP** 的刚性功率底噪）。

  * **Flex 1**：关键但微幅柔性任务，在 **3\~6 小时** 窗口内仅容忍 $\le 10\%$ 减速。

  * **Flex 2**：中度柔性任务，容忍 $\le 25\%$ 功率削减。

  * **Flex 3**：批处理与预训练任务，可在数小时窗口内减速或平移 $\le 50\%$。

## 3. 达产阶段（Phased Energization）与真实电网接入协议参数

### 3.1 变电站分期通电与受限站点实证数据（Camus / Princeton ZERO Lab / encoord, 2025）

在 [**Brancucci et al. (2025)《Flexible Data Centers: A Faster, More Affordable Path to Power》**](https://cdn.prod.website-files.com/60dbdcca2e4b1919e8894fa5/6930abf1be0f36db6fc27157_Whitepaper%20-%20With%20Appendix.pdf) 中，研究团队利用 PJM 某电力公司的**真实输电网模型与历史时序 SCADA 数据**，对 6 个候选站点接入 **500 MW 超大规模数据中心**（实际峰值负荷约 **435 MW**，预留 65 MW 裕度）进行了仿真：

* **建设周期与输电升级的阶段错配（Stage Mismatch）**：数据中心建设与标准接入仅需 **2 年**，而主网输电升级与新电源并网需 **5\~7 年**（全美范围 2\~10 年，且高压升压变压器交货期已达 [**160 周以上**](https://safeguard.sh/resources/blog/what-a-data-center-needs-to-connect-to-the-grid-steps-equipment-cost)）。在长达 3\~5 年的过渡达产期内，数据中心必须依赖“刚性 + 条件柔性（Firm + Conditional Firm）”协议运行。

* **4 个受限站点的实证容量与削减参数**：

  * **可用刚性容量（Firm Capacity** $S^{\text{firm}}$**）**：在 500 MW 申报容量中，现有电网可直接提供的刚性容量仅为 **154 MW \~ 326 MW**（占 30.8% \~ 65.2%），其余 **174 MW \~ 346 MW** 必须作为可削减的柔性容量接入，直至输电升级完工。

  * **全年阻塞总时长**：全年仅在 **7 \~ 35 小时**（远低于全年小时数的 1%）发生输电越限。

  * **分站点单次最大持续时长（决定算力 SLA 是否违约的关键分水岭）**：

    * **轻度/中度受限站点（Koala, Whale, Pony）**：单次削减持续时间不超过 **4 \~ 5 小时**。其中 **Koala 站点**全年累计削减 **7 小时**，峰值削减需求 **109 MW**；其最优配置包含 **25% 算力柔性（上限 20 小时/年）** + **49 MW / 196 MWh（4小时）储能** + **26 MW 光伏** + **11 MW 燃气轮机**。报告特别指出：Koala 的削减虽可单独靠 25% 算力柔性覆盖，但会耗尽全部 25% 算力调节裕度，不留任何容错空间。

    * **重度受限站点（Hare）**：单次削减事件持续长达 **16 小时**，远超常规算力任务的日内推迟极限，必须配置本地电源或跨区转移。

* **生产集群逐步达产实证（Alibaba Trace）**：在 [arXiv:2609.05406v1](https://arxiv.org/html/2609.05406v1) 中，15.5 万卡集群在 185 天内以阶跃式分期投运（Capacity Steps）的方式从首周均值的 **46.28 MW** 增长至末周均值的 **64.25 MW**（增幅 **+38.84%**，包含 6 个明显的容量稳定平台期 Plateaus），负荷率高达 **0.820**。

### 3.2 真实电网柔性并网合同（FCA）与调度规程参数汇总

| 电网 / 监管机构与合同名称 | 适用负荷门槛 | 指令通知提前量 (Notice Time) | 单次最大持续时长 ($H^{\text{consec}}$) | 年度/周期调用上限 ($H^{\text{inter}}_{\max}$ / $\phi_{\max}$) | 爬坡率与恢复间隔约束 | 文献与法规来源 | 
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | 
| **JHU / EPRI DCFlex 标准分层契约模型 (Layer A/B/C)** | 超大规模算力节点 ($30\%$ Firm / $50\%$ Flex / $20\%$ Inter) | 小时级日前/日内调度 | $4\text{ 小时}$ (C4 约束) | 年度能量上限 **5%** (占可中断层) / 年度小时上限 $480\text{ 小时}$ (行业范围 $180\sim 720\text{ h/yr}$) | 每小时最大削减深度 $\delta_{\max} = 30\%$；每小时爬坡率 $\rho^{\text{dc}} = 25\%/\text{h}$；允许时段 16:00–21:00；**最小事件恢复间隔** $R^{\text{rec}} = 12\text{ 小时}$ | [Khanal et al. (2026) Table 7](https://arxiv.org/html/2608.19622v1) | 
| **德州 ERCOT SB 6 (16 TAC §25.194) & SCED 实时调度** | $\ge 75\text{ MW}$ 大型负荷 | QSE SCED 实时指令：$5\text{ 分钟}$；共址电源切负荷：$30\text{ 分钟}$ | PUCT 规则制定中（标准窗口 $1\text{ h}, 2\text{ h}, 4\text{ h}$） | 紧急状态强制远程跳闸（DNP3 / IEC 61850 硬件闭锁）+ 4CP 尖峰规避 | 要求分阶段协调切除（Staged shedding）并满足 NOGRR 282 故障穿越 | [NFM Consulting SB 6 Guide](https://nfmconsulting.com/knowledge/texas-sb6-large-load-ercot-data-center-compliance/) / [Electric Era](https://electricera.tech/resources/data-center-flexibility-speed-to-power-and-profitability-via-autonomy-first-software-controls) / [Data Center Power Playbook](https://www.datacenterpower.ai/) | 
| **Indiana Michigan Power (I&M) 与 Google 专项合同** | 超大规模数据中心专项需求响应合同 | 电网峰值预警触发 | **夏季上限** $12\text{ 小时}$  **冬季上限** $15\text{ 小时}$ | 合同期内调用次数不设硬上限（Unlimited curtailments） | 按季节限定单次最长持续窗口 | [Large-Load Grid Integration Section 6](https://www.largeloadguide.com/section-28.html) | 
| **英国国家电网 NGED ANM 柔性并网规程** | 对阻塞灵敏度 $\ge 5\%$ 的新并网大负荷 | ANM 自动实时闭环控制（秒/分钟级） | 取决于主变 SGT 季节性热极限 (PEL) | 2023年新规后设年度削减小时上限（超限需赔偿，输电网 Technical Limits 除外） | **LIFO（后进先出）队列原则**：最新达产并网的阶段优先被削减；计及 0.95 功率因数与主变三级绕组限制 | [NGED DSO Curtailment Guidance](https://dso.nationalgrid.co.uk/downloads/15104/nged-curtailment-analysis-data-usage-guidance.pdf) / [Gridcog GB & Ireland](https://www.gridcog.com/blog/flexible-grid-connections-data-centres-gb-ireland) | 
| **爱尔兰 EirGrid / CRU 大用户并网规程** | $\ge 10\text{ MVA}$ 数据中心 | $2\text{ 分钟}$ 确认指令，$5\text{ 分钟}$ 内完成削减 | 无硬性上限（直至系统约束解除） | 无年度削减上限且无赔偿（除非配建 100% 可调度电源并实现 80% 新增绿电匹配） | 严苛实时响应 | [Gridcog GB & Ireland](https://www.gridcog.com/blog/flexible-grid-connections-data-centres-gb-ireland) / [Large-Load Grid Integration](https://www.largeloadguide.com/section-28.html) | 
| **北美 AESO 与欧洲 Energinet 并网导则爬坡限制** | 大容量负荷并网点 (POI) | 实时连续约束 | 全时段运行约束 | 全年连续生效 | **AESO 严格限制负荷爬坡率** $\le 10\text{ MW/min}$；**Energinet 限制** $\le 60\text{ MW/min}$ | [arXiv:2609.11649v1 Section II-B](https://arxiv.org/html/2609.11649v1) | 

## 4. 与你现有代码变量（`stage_physical_reduction`）的直接映射方案

为了在不引入沉重求解器的前提下，打破你在 `stage_physical_reduction_v1_findings.md` 中发现的“逐小时容量压缩等价性”，可以直接将以下三个实证关系写入 `v2` 核验脚本：

1. **用持续时长相关的实证回滚效率** $\eta(h)$ **替代常数** $\eta$：

   * 在现有模型中，削减 $q_t$ 产生债务，无调用时段按 $\text{debt}/\eta$ 恢复。

   * 直接引入 [Li et al. (2026)](https://arxiv.org/html/2609.05406v1) 的 Checkpointing 损耗公式：当一次电网调用持续 $h$ 小时（或通知提前量 $\Delta \tau < 15\text{ min}$ 触发非优雅中断）时，实际注入账本的算力债务为：
     

     $$
     \Delta \text{Debt}(h) = \left(1 + \frac{T_{\text{ckpt}}}{2h}\right) \sum_{\tau=t}^{t+h-1} q_\tau, \quad T_{\text{ckpt}} = 1.0\text{ h}
     $$

   * 这使得 $q_t$ 的代价依赖于**连续调用持续时长** $h$**（跨时状态）**，单个小时的标量 $C_t$ 无法表征短促频繁调用（如 $h=1\text{ h}$，附加 50% 算力回滚债务）与单次长调用（如 $h=4\text{ h}$，附加 12.5% 算力回滚债务）之间的本质差异。

2. **用实证持续时长衰减乘子** $p_{h,\alpha}$ **约束连续削减深度**：

   * 引入 [Li et al. (2026) Table 2](https://arxiv.org/html/2609.05406v1) 的 $p_{h,0.95} = [0.85, 0.83, 0.79, 0.74, 0.68]$（对应 $h \in \{1, 2, 4, 8, 24\}$ 小时）以及 [Khanal et al. (2026) Layer C](https://arxiv.org/html/2608.19622v1) 的最大连续调用时长 $H^{\text{consec}} = 4\text{ h}$、最小恢复间隔 $R^{\text{rec}} = 12\text{ h}$、爬坡率 $\rho^{\text{dc}} = 0.25/\text{h}$。

3. **用分阶段 Firm/Conditional-Firm 比例映射达产组合（`fast/slow × on_time/delayed`）**：

   * 对标 [Brancucci et al. (2025)](https://cdn.prod.website-files.com/60dbdcca2e4b1919e8894fa5/6930abf1be0f36db6fc27157_Whitepaper%20-%20With%20Appendix.pdf) 的 500 MW 分阶段接入实证：将 `on_time` / `delayed` 输电升级映射为刚性容量底线 $S^{\text{firm}} \in [154, 326]\text{ MW}$（占比 $30.8\% \sim 65.2\%$），将 `fast` / `slow` 算力投运映射为 [Li et al. (2026)](https://arxiv.org/html/2609.05406v1) 中 $+38.84\%$ 的阶跃式 GPU 达产曲线（含 20% 分配态 GPU 刚性待机底噪 $\phi = 0.20$ 与 43% TDP 在线推理刚性底噪）。

## 5. 本地数据位置与获取状态

2026-11-09 已按本手册清单把可公开获取的来源落到 `data/raw/`：

- [原始数据索引](../../data/raw/EMPIRICAL_GRID_TASK_DATA_INDEX_20261109.md)
- [获取与校验清单](../../data/raw/empirical_grid_task_acquisition_20261109.json)

已落盘：ASI/Alibaba 2026 衍生包与 49 MB 聚合表、Tiered-DC-CEM v2 完整包、ICARUS-DC、ICARUS-PJM、Camus/Princeton PJM 报告、核心论文与可访问的行业网页。

未获取：NLR 原始 ZIP（官方站点 TLS 握手失败，见 `data/raw/nlr_genai_power_2026/v2/ACQUISITION_STATUS.json`）、NGED 与 NFM 页面（HTTP 403）。这些来源不得按“已下载”引用，也不能据“未获取”反推其内容不存在。

数据落盘不改变本手册第 2—4 节中各项的证据等级：重建功率、论文假设参数和由本手册推导的映射仍需按 `SOURCE_OBJECTS.json` 与正文核验后使用。
