# 电网—任务资料适用性与本地数据核查

2026-11-09。只读来源与字节核查后形成的评估；不修改用户三份分析、不运行模型、不下载新数据。

## 判断

资料有用，尤其是ASI小时级eligible功率、持续时长/可靠性曲面、硬件试验和Camus接入事件范围。大部分公开资料已在本地，但尚没有同址同钟的“任务期限—实际抢占—恢复功率—网络事件—设备投运”完整配对数据。参数JSON目前是候选资料库，不能作为已校准模型配置直接使用。

## 实际文件核查

获取清单23个文件全部存在，字节数全部匹配，SHA-256全部匹配（包含426,291,296字节ICARUS-PJM与1,268,476,882字节CEM压缩包，流式读取校验）。ZIP检查了成员目录，本轮未重复整包CRC测试。依据：data/raw/empirical_grid_task_acquisition_20261109.json。不能用该清单覆盖未列入清单的文件。

|来源|本地位置（相对data/raw）|实际已有|尚缺/限制|
|---|---|---|---|
|ASI v1.0.1|asi_trace_power/v1.0.1/upstream/|9.82MB源码/衍生产品ZIP、50.77MB pod聚合Parquet|未下载约351GB原pod表；没有抢占—恢复现场测试，聚合表不含任务ID与合同deadline|
|Tiered-DC-CEM v2|tiered_dc_cem/v2/upstream/|1.268GB src.zip、说明与许可；PJM/Korea输入/配置/结果|与指南旧Zenodo编号不完全同版；论文参数含假设，不是统一合同实测|
|ICARUS-DC|icarus_dc/327ef39ada1cff606ca191c3ce56f20224b92c3f/upstream/|固定commit的完整公开ZIP；DCS_PJM表含Power、Year Built等|容量/年份存在缺失和未来计划，不是分批设备实际投运轨迹|
|ICARUS-PJM|icarus_pjm/0cb6a1af86e2bdfc1d160f44b6e4a7518ca3ffe3/upstream/|426MB完整公开ZIP，网络/分区/时序数据|不与Alibaba任务、Camus匿名站点一一配对|
|Camus/PJM|camus_flexible_data_centers_2025/v1/upstream/|whitepaper.pdf与HTML|原始SCADA和网络模型未公开，不能复现匿名站点逐时事件|
|NLR GenAI|nlr_genai_power_2026/v2/|失败状态记录；论文在docs/literature|原始1.07GB ZIP不在本地。另有已处理metadata catalog，不能把目录存在等同于原始功率日志已获取|
|Williams硬件示范|docs/literature/empirical_grid_task_20261109/2606.25098v1.*|论文PDF/HTML|本次清单未见原始硬件遥测、任务与恢复日志|
|规程/合同|google_operational_flexibility_evidence_v1/current/upstream/|多份行业网页|NGED与NFM获取失败；若干法规条目仍是二手来源，须核官方版本、适用主体与条件|

NLR已处理summary位于 data/processed/model_inputs/nlr_genai_power_profiles_v2/summary.json：2467项测量profile元数据、11项分组统计、8项合成设施profile；其中deadline_observed、checkpoint_state_observed、recoverable_fraction_observed、dynamic_ramp_calibration_ready均为false，source_aggregation_recomputed=false。不是从本地原始NVML日志重算的动态校准。

## ASI字段与版本风险

已读取Parquet footer和ZIP内衍生产品schema：

- pod_hourly_agg.parquet：**1,479,356行**，字段day/hour/cluster_id/GPU型号/job_type/priority/state/n_pods/gpu_hours/S0/S25/S50/S75等17列。无逐任务ID、原期限、checkpoint时间或恢复实际功率。
- fleet_hourly_power.parquet：4440行；含have、P5/P50/P95、base与IT功率。
- envelope_hourly.parquet：4440行；含good、floor/shift/curtail/standby、idle-retained、node-sleep等不同电气边界。
- envelope_cluster_hourly.parquet：71040行。
- k_surface.parquet：660行；含h、alpha、k_obs、标量/打乱/独立集群反事实与窗口数。

指南和论文写858,816行聚合表，当前文件footer不符。4440时间格与4439有效观测也应通过have/good核对，不能直接删行。字节校验通过只说明与本地下载清单一致，不能解除版本/筛选范围问题。当前上游GitHub README另已显示v1.1.0；本地应保持v1.0.1固定，复现前明确比较版本。

## 必须收缩或修正的科学表述

1. **重建MW不等于设施功率实测。** ASI根据生产资源轨迹与功率曲线重建MW，PUE、idle与online floor含模型锚点/不确定性；可作有来源的参数范围，不能称同一站点已测标定。
2. **K(alpha,h)不等于恢复可交付性。** 原文§2.4以逐小时eligible功率C_t在连续窗口的最小值定义K。它反驳固定负荷比例能匹配所有持续时长，不反驳时变C_t表示；也没有验证响应后任务恢复或SLA。原文Fig4说明是historical eligibility，实际realizable fraction尚需现场测试。
3. **checkpoint与恢复速度是假设推导。** 原文Appendix D明确checkpoint interval和absorption rate为illustrative contract parameters。1h、2.326MW、4.49h、8.49h不能直接称为实测运行限制。公式还依赖全量回补、均匀checkpoint相位等前提，不能作为所有任务通用eta(h)。
4. **时长相关K不宜逐小时硬乘。** 它是窗口/可靠性统计量，不是每个小时的确定性可用上限；须区分事件承诺、条件信息和样本外覆盖，避免把曲面与原始时序重复降额。
5. **15分钟示范爬坡不是普适物理下限。** 硬件示范同时报告更快的应急响应，应按任务类型、控制方式和SLA解释。
6. **0.30/0.50/0.20、C1–C5不是统一标准合同。** 它们是CEM的分类和参数假设/敏感性设置。聚合cyclic backlog及能量容量界也不等于逐cohort原期限保证。
7. **跨来源组合只能标为情景配对。** PJM站点、Alibaba集群增长、NLR硬件功率不共址、不共任务。观测到舰队功率增长不能直接解释为设备投运增长。
8. **同行评审状态应另核。** arXiv版面带会议名称不能单独作为已接收/已发表证明。JSON metadata中全面替换为peer-reviewed empirical traces的目的表述过强。

主要核查原文：[ASI](https://arxiv.org/html/2609.05406v1)，§2.2/2.4、Fig4、Appendix D；[硬件示范](https://arxiv.org/html/2606.25098v1)；[CEM](https://arxiv.org/html/2608.19622v1)，§4.4；[ASI仓库](https://github.com/meiyilutaustin/asi-trace-power)。法规未在本轮确认为正式可用参数。

## 对当前论文最有用的安排

第一优先：固定ASI版本并核对聚合表行数/字段/有效时间，复现其已有持续时长曲面和电气边界，建立可信基准。直接使用小时衍生表不需要先下载351GB原表。

第二优先：按可获得性分别建立eligible MW证据、硬件响应证据、任务恢复假设与网络事件情景；checkpoint等仅做显式敏感性，等待实测或任务记录后校准。

第三优先：再检验阶段条件、重复调用与原期限债务是否改变已有持续时长/可靠性曲面下的承诺决策。ASI已直接研究固定比例高估，不能把复现该结果算作我们的新贡献。

这批资料足以做来源扎实的开发基准和参数分层，不足以宣称真实同址闭环已校准，也没有自动解决TSG新颖性问题。
