# Google ClusterData2019 与 PowerData2019 适用性审计 v1

状态：`DRAFT_NONAUTHORITATIVE`
日期：2026-09-12
范围：公开来源/数据合同审计、授权的有界公开数据补充与 DRAFT non-authoritative 短验证；零 solver、零付费查询

本审计判断 Google 2019 集群与功率数据能否补强 RQ2 continuous successor。它不修改冻结协议、
输入包、模型、阈值、结果或 gate，也不注册 deadline、flexibility、recovery、accounting period 或
power-to-MW 映射。

## 1. 当前适用性建议

本轮不切换主数据源。当前建议仅把 Google 数据作为**同提供方 CPU 使用量—PDU 归一化功率的
外部稳健性候选证据层**；应先修复数据合同，再比较其 CPU 主场景与 Alibaba GPU 主工作负荷的
适用范围。Google 数据不能直接补齐真实业务期限和恢复预算。

| Google 字段或材料 | 可支持 | 不支持 |
|---|---|---|
| `measured_power_util` | PDU/设施侧归一化实测功率形状 | 绝对 MW、未限功率需求、可削减功率 |
| `production_power_util` | CPU 驱动的 production-power 估计诊断 | 第二套独立功率实测、真实柔性 |
| `average_usage.cpus` | 不等长采样区间的平均 NCU usage | GPU 使用量、IT 或 PDU 功率 |
| `priority < 120` | 官方 notebook 的 `cappable` 候选分层 | 合同柔性、deadline、恢复能力 |
| 调度事件和 `scheduling_class` | batch/latency 与提交、驱逐、完成状态 | 完成时限、驱逐后债务已偿还 |
| Google 24 小时生产规则 | 另一生产系统的外部机制先例 | ClusterData2019 逐任务观测标签 |

因此 Google 可用于归一化功率形状、CPU—功率描述性关联和 priority 候选上下界。不得据此直接生成
`flexible_fraction`、`service_deadline`、`maximum_recovery_power`、`recovery_efficiency`、
`event_count_limit`、`energy_budget` 或 `accounting_period`，也不得把 CPU 关联移植为 Alibaba GPU
逐任务功率函数。

## 2. 官方来源和语义

仓库锁定 Google `cluster-data` commit
`3f6a61d380dc4ea847416d5414c5fa499f830b9d`：

- [PowerData 入口](https://github.com/google/cluster-data/blob/3f6a61d380dc4ea847416d5414c5fa499f830b9d/PowerData2019.md)
- [PowerData 字段文档](https://github.com/google/cluster-data/blob/3f6a61d380dc4ea847416d5414c5fa499f830b9d/power_trace_documentation.pdf)
- [官方联合分析 notebook](https://github.com/google/cluster-data/blob/3f6a61d380dc4ea847416d5414c5fa499f830b9d/power_trace_analysis_colab.ipynb)
- [ClusterData 入口](https://github.com/google/cluster-data/blob/3f6a61d380dc4ea847416d5414c5fa499f830b9d/ClusterData2019.md)与[详细 v3 文档](https://drive.google.com/file/d/10r6cnJ5cJ89fPWCgj7j4LtLBqYN9RiI9/view)
- [v3 schema](https://github.com/google/cluster-data/blob/3f6a61d380dc4ea847416d5414c5fa499f830b9d/clusterdata_trace_format_v3.proto)

本轮内存读取的 Power PDF、Cluster PDF、notebook SHA-256 分别为
`06011d9dd34b7649944f092b2b15fdd83976a6be3d7e358c128ef49666f90743`、
`17267c7c634a6ee01146b8032bacc26d9c7354e7b3bdb6a48fc0cbb69f02d6f9`、
`437d63229469d8525ffbf6e57603cd1667502a2a3f6beadc7f3d05e34c1dccc2`；PDF 未写入仓库。

PowerData 覆盖 10 个 clusters、57 个 power domains；其中 55 个属于 ClusterData 的八个 cells，两个为
power-only MVPP。每域有 8,928 个五分钟区间。两个 traces 使用同一个“正式 trace 起点前 600 秒”epoch；
正式起点 2019-05-01 00:00 Pacific Time 对应 `time=600000000`。power `time` 是五分钟区间起点。

功率字段为 usage/capacity 比值，PDU capacity 未公开，因此不能跨 PDU 求和成系统 MW。
`measured_power_util` 包含服务器和 floor cooling 等设施负荷；`production_power_util` 由 CPU usage 与
idle/busy power 插值估计并包含 cooling，不是独立实测。Cluster schema 有 priority、scheduling class 和
SUBMIT/QUEUE/SCHEDULE/EVICT/FAIL/FINISH 等事件，没有 deadline 字段。

## 3. 本地已有数据

`data/raw/google_power_2019/2019/upstream/` 已有 57 个功率域和 mapping，总压缩大小 3,254,733 bytes，
共 508,896 条功率记录和 96,616 条映射。source manifest SHA-256 为
`fc11c3a59cc078799bcc289cc40579025d8b82b5c009679b1690f987b91c7c47`。

本轮未重复下载。远程 HEAD metadata 与本地只读实检为：

| 对象 | generation / bytes / MD5 | 本地 SHA-256 | 本地检查 |
|---|---|---|---|
| `cella_pdu6.csv.gz` | `1708543216788998` / 45,392 / `e196e2b48d51dfbea016bce4ef08110c` | `7c56bcfd1694dadc2abb3d4fd6ba179fb96cf45adea6288b47667e12b1fe734e` | 8,928 行；时间唯一，排序后步长均为300,000,000 us；原始行未排序 |
| `machine_to_pdu_mapping.csv.gz` | `1708543379408517` / 532,199 / `8a8cf3df29b11b0c942dbc5197289391` | `69b88e5662348030b074fef2008a4f2c16927a68b2d218a8c7c5cf350dc0aa8d` | 96,616 行；96,614个`(cell,machine_id)`键；2键多PDU |

完整 join 必须使用 `(cell,pdu,machine_id)`。现有 `cell f/pdu17/day-0` ClusterData 提取也在本地。
历史三次成功 BigQuery jobs 累计 processed/billed 为 551,002,439,062/551,004,667,904 bytes；这是
2026-07-16 已归档作业，不是本轮查询。

## 4. 三个未关闭的数据问题

### 4.1 quality flag 来源冲突

Power PDF 对 `bad_measurement_data` 和 `bad_production_power_data` 的文字说明称 false 为低置信度，
但字段名和官方 notebook 使用 `WHERE NOT bad_measurement_data AND NOT bad_production_power_data`。
现有 processor 按 notebook 把 false 当可用。本轮不猜测、不翻转旧产物；未来新输入使用 flag 前，须取得
官方勘误或可判定方向的版本说明。预注册双极性敏感性只能作条件诊断，不能据此关闭真实 flag 语义门。

### 4.2 legacy day-0 配对确定错位 10 分钟

现有 config/SQL 把 ClusterData raw window 固定为 `[0,86400s)`，并按 raw `time/3600s` 分为 0–23 小时；
power processor 取 `[600s,87000s)` 后按每 12 个样本分小时，再直接 zip 两侧。结合共同 epoch，可确定：
CPU hour 0 覆盖实际 `[-10,50)` 分钟，power hour 0 覆盖 `[0,60)` 分钟，固定错位 10 分钟。现有测试只锁定
两侧各自窗口，没有共同 interval 不变量。

这推翻 legacy artifact 的“同步配对已验证”解释，但不自动作废独立使用 Google power shape 的下游结果。
canonical bytes 本轮保持不变；修复必须使用 versioned successor，并按共同 epoch 上的 interval overlap 对齐。

### 4.3 当前环境重建不一致

在当前 Windows 审计环境合跑既有三组 Google source/processing tests 得到
`1 failed, 9 passed in 11.80s`。唯一失败是 real-day0 atomic processing 的重建 hash 与 config 不符，
并按设计 fail closed；另一次独立复算也得到不同重建 hash。source metadata 和 canonical files/config hashes
自身均未漂移。逐字段复核把差异限定为约 15 位浮点序列化的末位，priority CSV 影响 1 个字段，pair CSV
影响 11 个字段，核心 aggregate 未变。故当前未关闭的是 byte-level cross-environment floating serialization
reproducibility，不是 raw 损坏、科学数值变化或数学不可行。第 7 节的 versioned successor 已隔离修复
新诊断的 deterministic arithmetic/serialization；它不改写 legacy bytes，故仍不能称旧 day-0 包在当前环境可重现。

## 5. 获取渠道与零付费后续建议

概览 README 称约 2.4 TiB 的 ClusterData 只通过 BigQuery 提供；详细 v3 PDF 又提供按 cell/table/shard
从 GCS 下载 JSON 的方法。不能再把 BigQuery 写成唯一渠道；但单个 shard 不保证完整有序 chronology，不能
冒充完整 workload。

建议的后续顺序如下。用户随后授权了第 1、2 项的短时 DRAFT 开发，其可证明范围和结果见第 7、8 节；
其余项目仍未预注册或取得具体执行权限：

1. 零查询固化 day-0 hash drift 的 reproducing test，并设计按共同 epoch + interval overlap 对齐且采用
   deterministic arithmetic/serialization 的 versioned successor；不得为匹配旧 hash 调排序、舍入或时间边界。
   同时诊断现有 Cluster raw 是否覆盖共同时间轴上的完整 24 小时；若末端 10 分钟缺失，裁剪后的共同交集
   不得称为完整 24 小时，补齐 coverage 需另行授权获取上游数据。
2. 仅在用户授权且 versioned successor 通过独立复核后，才用已验证的共同覆盖区间做
   CPU—measured-power 描述性关联；只有 raw coverage 完整时才可称 24 小时。priority 和 machine capacity
   若未重建，必须保留来源绑定并显式维持 unknown/incomplete 状态。
3. 只有需要 clean-room 抓取验证时，才在临时目录获取官方示例 `cella_pdu6` 与 mapping；两者合计
   577,591 bytes，且本地已与当前远程 generation/MD5 相符，不能覆盖 raw。
4. 可选 GCS shard pilot 只验证 schema、字符串化 int64、跨窗 interval 和排序。先固定对象与大小并取得授权；
   单 shard 不生成小时总量、完整 PDU population 或 deadline 分布。
5. 如免费 shards 不能证明完整 coverage，则停止。未来 BigQuery 必须另行授权 dry run 和
   `maximum_bytes_billed`；SQL `LIMIT` 不作为扫描费用上限。

## 6. 当前状态

```text
google_power_source_available=true
google_power_source_integrity_verified=true
google_cluster_day0_local_extract_available=true
google_cluster_day0_temporal_alignment_verified=false
google_cluster_day0_reproducible_in_current_environment=false
google_cluster_23h_alignment_diagnostic_available=true
google_cluster_23h_cross_process_reproducible=true
google_cluster_23h_descriptive_association_available=true
google_cluster_machine_events_public_supplement_available=true
google_cluster_machine_capacity_complete=false
google_cluster_usage_pilot_downloaded=true
google_cluster_usage_pilot_content_verified=false
google_pdu17_multiday_hourly_cpu_acquisition_available=true
google_pdu17_multiday_unfiltered_cpu_power_capacity_alignment_available=true
zeus_training_power_public_supplement_available=true
google_cluster_complete_24h_pair_available=false
google_power_quality_flag_semantics_resolved=false
google_absolute_power_mw_available=false
google_flexibility_observed=false
google_deadline_observed=false
google_recovery_parameters_observed=false
google_gpu_workload_observed=false
google_continuous_successor_model_input_ready=false
full_joint_service_continuation_ready=false
continuous_scientific_protocol_registered=false
formal_result=false
paper_claim=false
security_certified=false
```

第 7 节仅关闭 23 个完整 raw-clock 小时的时间对齐与新输出确定性问题。不得借本审计改写 sealed v5、
continuation v1、既有 canonical bytes 或正式结果。

## 7. 23 个完整小时的 DRAFT successor

本地 `records.csv.gz` 共 1,665 行，其中 CPU 仅剩 `24×2×7=336` 行最终小时聚合；没有
`start_time/end_time/fragment/average_usage`，不能拆为五分钟，也不能从 hour 0 精确裁去最初 10 分钟。
在共同 raw clock 上机械求 CPU `[0,86400s)` 与 legacy power `[600s,87000s)` 的最大完整小时交集，得到
`[3600s,86400s)`：CPU source hours 1–23，与 276 个五分钟 power intervals 形成 23 个完整小时。
相对正式 trace 起点 `600s`，实际覆盖为 `[00:50,23:50)`，不是 midnight day、24 小时或 continuous input。
CPU hour 0 被整小时排除；legacy power 窗口在共同区间前后分别排除 10 和 2 个样本。

新增 `google_power_workload_alignment_successor_v1` 独立处理器，不导入或修改 legacy processor。它从上述
源边界机械推导交集，精确锁定 300 秒步长、600 秒 epoch 和 legacy 窗口，拒绝缺失/重复 timestamp、错 PDU、
hash 漂移以及超出官方 `[0,1]` 字段合同的 `measured_power_util`。全部 Decimal 求和、除法和量化使用局部固定
50 位 `ROUND_HALF_EVEN` context；CSV 固定 LF 和 12 位 power mean。受控输入行重排以及两个独立 Python
进程均产生相同 bytes。输出以 staging 原子发布，不生成 production manifest、lease 或 PASS。

23 行 pair 只汇总已提取人口的 CPU lower/upper bounds；`cpu_subhour_disaggregation_performed=false`、
`priority_strata_reconstructed=false`、`machine_capacity_reconstructed=false`、
`population_is_complete_pdu_workload=false`。priority 与 machine event 仍由锁定 raw source 提供 provenance，
没有用于 CPU normalization。276 个候选 power 样本原样保留 flag 计数：measurement false/true 为 276/0，
production false/true 为 0/276；由于第 4.1 节来源冲突，未据此赋予 quality eligibility。

配置、实现和机器诊断分别位于：

- `configs/google_power_workload_alignment_successor_v1.DRAFT.yaml`；
- `experiments/process_google_power_workload_alignment_successor_v1.py`；
- `results/tables/google_power_workload_alignment_successor_v1_non_authoritative/`。

`aligned_hourly_pair.csv/summary.json` SHA-256 为
`54d664f2fa261413c1dfb5c05479d6aa6977e74ea8a6f36c3a5f41dba79f5930`/
`e7d6edad6f2e5abf4ad07b096b2c6c584156532fbfea452648ce78d07b551d53`；summary 绑定 config/implementation
SHA-256 `dc8285d3799d62c9ecebee47ecdf480f461d9f0f0ea033310fab88fbea945ae1`/
`7011b96f3141a3937b49a2b6493b00ee01a05e770ed2fdf922d7bee1e76054d5`。

新 successor focused 为 `11 passed in 1.26s`，连同 Google source/processing 相关回归为
`14 passed in 14.19s`。legacy processor 单独复跑仍为 `1 failed, 6 passed in 0.66s`，失败仍是已登记的
浮点末位 artifact hash drift；没有 xfail、改阈值或借新路径覆盖它。本轮零 solver、零外部下载、零查询，
所有 formal/result/claim/security 和 continuous model-input gates 保持 false。

## 8. 23 小时 CPU—measured-power 描述性关联

在第 7 节的锁定 pair 上，对 source hours 1–23 的 23 行全部样本原样分析，不按 `bad_*` flag 筛选。
每个 CPU 小时端点是 `2 collection_types × 7 priority_tiers=14` 行的小时总和；单位为 NCU，范围只覆盖
已提取且人口不完整的 source population。`measured_power_util_mean` 是每小时 12 个五分钟 PDU 归一化实测
功率比值的均值。分析分别计算 CPU lower/upper 端点与 measured power 的 Pearson 和使用平均秩处理 ties 的
Spearman；两端点结果不是相关系数的识别上下界。

23 行描述统计和系数为：

| 序列/端点 | minimum | maximum | mean | Pearson vs power | Spearman vs power |
|---|---:|---:|---:|---:|---:|
| CPU lower (NCU) | 688.10765921884108748542 | 819.99072570032545898353 | 764.722633326445243064 | 0.962184945123159126 | 0.962450592885375494 |
| CPU upper (NCU) | 688.10765956401822748542 | 819.99073299778825998353 | 764.722634757912693568 | 0.962184943013110584 | 0.962450592885375494 |
| measured power (normalized PDU ratio) | 0.694000000000 | 0.758916666667 | 0.738507246376869565 | — | — |

原始 276 个 power 样本的 measurement false/true 为 276/0，production false/true 为 0/276；这些只作
未过滤计数，flag 方向冲突仍未关闭。`missing_cpu_overlap_seconds` 总计 0，非零小时 0；
`cpu_conflict_overlap_seconds` 总计 109，涉及 22 个小时。overlap seconds 是跨 fragment/instance 聚合量，
不是 23 小时 wall-clock coverage；missing 为 0 也不证明 PDU 人口完整。

实现与机器结果位于 `experiments/analyze_google_power_workload_23h_v1.py` 和
`results/tables/google_power_workload_23h_descriptive_v1_non_authoritative/summary.json`。实现/summary SHA-256
分别为 `fdf821a074ce7b4cfaeefc306500b76ec100a830ae11557d07df4bafd5ab9a60`/
`030626393f2ac96fcfd91f151017ad8b7c5bafa3476dd1daf67a3b500e8e23e2`；summary 继续绑定第 7 节的 pair、
alignment summary/config/implementation 四个 hash。focused 与 alignment 回归合跑为 `23 passed in 1.06s`，
独立 reviewer 无新增 finding。

本检查没有计算 p-value、confidence interval、lag、拟合或标定，也没有选择参数或估计 flexibility。高描述性
相关不能解除 quality flag、population completeness、24h/multiday、absolute MW、deadline、recovery、
continuous model input、formal result、paper claim 或 security certification 任一 gate。

## 9. 有界公开数据补充：Google machine events 与 Zeus 训练功率

用户授权实际补充公开数据后，本轮分页读取 `clusterdata_2019_f` 的全部 16 页 object inventory，共 15,264 个
对象，并单独读取 `clusterdata_2019_schema` 的 5 个 schema。JSON 与 Parquet 是两套对象，不混合作为一份
数据求和。cell f 完整 inventory 为：

| table | JSON objects / bytes | Parquet objects / bytes |
|---|---:|---:|
| collection_events | 1 / 270,631,447 | 6 / 159,366,985 |
| instance_events | 239 / 44,636,950,553 | 1,180 / 14,100,104,301 |
| instance_usage | 1,575 / 990,791,658,431 | 12,259 / 447,312,709,954 |
| machine_attributes | 1 / 19,884,918 | 1 / 8,537,961 |
| machine_events | 1 / 792,540 | 1 / 452,862 |

全 JSON/Parquet 分别约 964.6/429.9 GiB，均超过本轮为控制资源自行采用的 1 GiB 下载范围（非用户预算）和
当时约 109 GB 的空闲磁盘。本轮
实际下载完整 machine-events JSON、同 bucket 后增的 Parquet 对象、5 个官方 JSON schema，以及字典序首个
36,464,842-byte `instance_usage` Parquet transport pilot。Google v3 PDF 第 14 页只文档化逐行 JSON gzip；
Parquet 仅视为同官方 bucket 的后增 transport candidate。临时 DuckDB 安装因镜像提供源码包且环境缺少
C++/NMake 而一次失败后停止，未修改锁定环境。因此两个 Parquet 对象只验证 generation、size、MD5、SHA-256
及 `PAR1` container magic，未验证与 JSON 的内容等价；usage pilot 的 schema、row count、time range、
chronology 和全表完整性均保持未验证。

官方 JSON 的 cell-f machine-events 全表有 49,603 行、12,201 台机器，event code 1/2/3 的计数为
30,380/18,472/751，对应 ADD/REMOVE/UPDATE。`time=0` 的 11,392 行是 trace 前 snapshot 特殊值，均为唯一
ADD 且有 capacity，不作普通时间排序。另有 716 条非零时刻首次 ADD 缺 capacity，均在 0.547676–7.007018 秒
后首次由 UPDATE 给出已知 capacity，中位延迟 1.8854475 秒；这些初始区间保持 unknown，不前填、后填或补零。
49,603 行均未出现 `missing_data_reason` 字段；schema 允许 NULL，因此不能把字段缺省写成观测的 NONE/0。

旧 mapping 中 cell f 有 12,203 台机器，其中 2 台无 machine event；pdu17 映射 1,295 台，time-zero snapshot
覆盖 1,221 台，其 normalized CPU/memory 合计为 1220.5/610.25。这只是已映射机器在 trace start 的规范化
available-resource snapshot，不是物理核数、PDU MW、完整业务人口或持续可用容量。

另按 Zeus 官方仓库 commit `f9db43227e1e5a3b4595bb4282f821890942b7bf` 下载 LICENSE、两份 README、
`run_single.py`、`summary_train.csv` 和 A40/V100/P100/RTX6000 四张功率表。训练表有 3,759 行、6 个
dataset-network pairs、63 个 batch-size configurations；distinct run 数分布为 1:2、2:2、3:2、4:5、
5:35、10:17，因此实际有 6 个配置少于 README 所述的至少 4 次。`target_epoch` 有 2,910 个整数和 849 个
字面量 `nan`；只记录为未给出达到 epoch 的 sentinel，其确切失败/删失含义未由当前来源关闭，且它不是业务
deadline。四张功率表分别有 453/476/270/410 行，字段为 GPU `power_limit` W、`time_per_epoch` s 和
`average_power` W；每个配置只测一次，不能冒充重复功率样本、server/facility/PDU 功率或生产集群时序。
Zeus 作者构造的 Alibaba workload mapping 不是观测的同任务、同钟 job-power 链接，本轮没有下载或采用。

原始来源 metadata、审计实现和机器 summary SHA-256 分别为 Google
`bdb2ab90cb6572bfc4567bbe4f2b93d7c613d8bd8ae5eaaf1f130b4c1dcf6d8c`、Zeus
`1e2c680d924cd5f9e8ce206a5357b49ed92152b6351ca34906f8c0db038b8214`、实现
`abd8eb341490193789ff22141d5388aa9246bf1eb3fe2cdc7904da3e717c856b`、summary
`472a2809807e0bdc10934a99dab3b6064c88f89add0945afd5917efe7a789334`。focused 为
`6 passed in 2.46s`。本轮实际新增 38,044,870 bytes（含两份 metadata），零付费查询、零 solver。

本节只新增 machine chronology 与受控 DNN GPU power/performance 的外部证据。Google完整 usage、capacity
completeness、absolute MW、业务 flexibility/deadline/recovery、连续多日输入和 Zeus 到 Alibaba 的观测映射
仍缺失；所有 continuous model/formal/result/claim/security gates 保持 false。

## 10. 全月公开数据准备包：功率原值、PDU17容量与GPU性能

在不改动第9节原始包和既有模型输入的前提下，新建了
`public_compute_multiday_v1_non_authoritative`。处理器固定使用仓库外已有 PyArrow 23.0.1，只读核验 cell-f
machine-events 的 JSON/Parquet：两者各49,603行，逐行顺序和规范化内容均完全相等。PDU17的1,295台映射机器
全部有事件；状态序列未发现非法转换。按共同 raw clock `[600000000,2679000000000)` 对每小时积分后得到744行
normalized available-capacity 证据。72个非零ADD后的短暂容量缺口保持unknown，合计117.081411 machine-seconds；
REMOVE不沿用其行内capacity，缺口未前填、后填或补零。该量不是物理核、MW、完整业务人口或可调容量。

57个PowerData域均保留8,928个五分钟区间，共508,896行，固定范围同为
`[600000000,2679000000000)`。输出同时保留measured/production原值及两列`bad_*`原flag，不作质量筛选。
全表flag组合`00/01/10/11`分别为392,364/116,508/15/9；来源冲突仍使flag方向unknown。
Zeus四GPU表合并为1,609行（A40/P100/RTX6000/V100为453/270/410/476），只增加
`time_per_epoch_seconds × average_gpu_power_w`的直接energy-per-epoch乘积；没有拟合、参数选择或Alibaba job映射。

另对12,259个usage Parquet对象按固定序号0/1/10/100/1000/6000/12000/12258保存generation-pinned
footer range。8个样本共5,027,931行，所有16个row group的时间区间与PDU17机器ID范围均相交，且六个必要列没有
column/offset page index，因此样本中不能按日期或PDU17谓词跳过任何row group。六列压缩量为46,916,555 / 
291,816,420 bytes（0.160774212089），线性外推全表约71,916,348,500 bytes；这是资源估计，不是全部12,259
对象的完整性证明。本准备包未提取全月PDU17 CPU。

公开业务证据另行锁定Google 2023 demand-response网页和arXiv:2106.11750摘要。前者披露欧洲五国在
2022-12至2023-03通常每日17:00–21:00降功率，并按小时给出限制、事件后重排任务；后者说明Google系统保留
overall daily capacity并使相应flexible workload在一天内完成。这些是实际调用窗口和系统设计边界，不识别
2019 cell-f或Alibaba逐job deadline、recovery期限或共享预算，也未写入模型参数。

处理器/summary SHA-256为
`92c727c4c2a275295ebf85039523e5ddc5ade599984f1c7333ce9ca6adbf42a0`/
`d3349e6b00cbd77c5b83f98bc208b90ff62612f1c2f185e1aade847970f18562`；三个数据表hash见summary。
focused为`11 passed in 29.77s`，独立复核为`11 passed in 22.60s`。本包中的BigQuery信息仅为未绑定session
observation，不是预算ledger；本包执行query jobs为0。完整PDU17 CPU、quality、population、MW、flexibility、
deadline、recovery、continuous model以及formal/result/claim/security gates保持关闭。

## 11. 全月 PDU17 CPU 小时聚合获取

用户授权按量查询并给出本任务累计 1 TiB 上限后，以固定作业
`google_pdu17_multiday_v1_5f0ddc384afe27ac`执行一次全月查询。SQL 使用共同 raw clock
`[600000000,2679000000000)`，相对起点划分 744 个整小时；只保留
`alloc_collection_id IS NULL OR 0`的 root usage 与 root instance events，并将 `machine_id`保留在
priority 的因果 identity 中。priority 仅按先前事件做 as-of 分段；NULL 或同刻多值保持 unknown/ambiguous，
不使用未来值回填。CPU 先折叠完全重复行，再以 `BIGNUMERIC`计算冲突端点和 interval overlap，最后才固定格式。

dry-run processed 为 554,760,728,186 bytes；实际 processed 相同，billed 为 554,761,715,712 bytes，
低于 600,000,000,000-byte 单作业上限和 1,099,511,627,776-byte 本任务累计上限。query cache 未使用；
两个 connectivity/oracle 验证作业均为零 processed/零 billed。公共原始表仍在 BigQuery；本地仅保存
10,416 行小时聚合和 1 行审计，压缩结果为 405,212 bytes。云端匿名临时结果为 2,388,300 bytes、10,417行，
按平台设置到期；本地绑定包不依赖其长期存在。

审计确认 PDU17 映射机器为 1,295 台，source usage 为 751,864,074 行，折叠后有
751,808,110 个 value groups。结果中保留 55,947 个 exact-duplicate value groups、6,659 个 CPU-conflict
usage groups、67,327,137 个 synthesized-priority groups和21个 unknown-priority groups；这些计数不能写成
“数据无缺陷”。不可归属的 priority event、usage key/time、CPU 值、fragment coverage/overlap/future-priority、
collection type 和 priority 范围等硬审计项均为0。小时网格的每个 lower endpoint 不大于 upper endpoint，
但端点不是统计置信区间。

版本化输入与实现位于：

- `configs/google_power_workload_multiday_v1.DRAFT.yaml`
- `experiments/sql/google_power_workload_multiday_v1.DRAFT.sql`
- `experiments/sql/google_power_workload_multiday_tiny_oracle_v1.sql`
- `experiments/fetch_google_power_workload_multiday_v1.py`
- `data/raw/google_power_workload_2019/multiday_v1_non_authoritative/upstream/`

config/SQL/oracle/implementation SHA-256 分别为
`594a32c8c708796ded88682bcc8e3b059ef44d246d0778d1c072dc37a69f5b3a`、
`5f0ddc384afe27accbd568830d70b924f850aea20527486e92f2f69e76d8a742`、
`db3367e901fd2392098e488a58bfc49d8a841a59c3b00a548d09a0412bee5913`、
`91bffda376d5ec6a3b78af59b8d825b1db7df2936510f0dcea6102f4cabbde56`；
`records.csv.gz`/`SOURCE_METADATA.json` SHA-256 为
`3c204c39cc099fb344a663801e2977adcc063ab988de465e8069a62ccd987ca0`/
`557e75d553a781bb556e5b1e1a972d36302790197f3bd90a0be562a525573a57`。重复执行入口只验证并复用同一
job/artifact，不重新提交。focused 联同相关 prepare/alignment/descriptive 回归为 `52 passed in 24.08s`。

本节关闭的是 `google_pdu17_multiday_hourly_cpu_acquisition_available=true`。它没有按未决 `bad_*` 方向选择
PowerData，也尚未形成新的全月 CPU—power 配对分析；root population 不等于完整 PDU 业务人口，normalized
CPU 不等于物理核或 MW。真实 flexibility、deadline、recovery、业务预算、连续模型输入以及
formal/result/claim/security gates 全部保持 false。

## 12. 744 小时 CPU—power—capacity 同钟配对

在第10、11节已绑定的本地工件上，新建
`google_power_workload_multiday_pair_v1_non_authoritative`，未发起查询、下载或solver调用。每个hour严格对应
共同raw interval `[600000000+h×3600000000, 600000000+(h+1)×3600000000)`。744行中的每行均嵌套
2种collection type×7种priority tier的14条CPU source strata，并原样保留各端点和missing/conflict/duplicate/
synthesized诊断字符串；另保存14条端点的小时总和，但不计算CPU/capacity比例。

每小时PDU17功率由12个连续五分钟样本以固定50位`ROUND_HALF_EVEN` Decimal求mean。measured和production
均保留，`bad_*`不筛选；8928个样本的flag组合`00/01/10/11`为6621/2307/0/0，其中194小时至少含一个
production flag=true，measurement flag=true涉及0小时。由于官方PDF与notebook的flag方向冲突仍未关闭，
这些计数不是quality eligibility判定。

capacity按同一hour key嵌套全部machine-second和normalized resource-time字段。16小时含unknown active capacity，
合计117.081411 machine-seconds，未填零或前后填补。CPU conflict overlap大于0的小时为711，missing CPU
overlap大于0为0，unknown priority tier有usage的小时为21；后两项只描述selected root-usage population，
不能证明完整PDU人口。源CPU全表审计中的55,947个exact-duplicate value groups、6,659个CPU-conflict groups、
67,327,137个synthesized-priority groups和21个unknown-priority groups继续保留在summary。

coverage另机械划分31个从raw trace起点开始的24小时block；每块固定24小时、336个CPU strata、288个power
样本和24条capacity记录。它们不是已识别的自然日，也未被选择为train/holdout。没有计算MW、headroom、
flexibility、p-value、拟合或恢复参数。

config/implementation/aligned/summary/README SHA-256分别为
`07f0cc04846bf39f170ecf4145e7ea64f4f791bf7f474933aa0107dbe9cc6746`/
`aef3134c8a3fdc93078fef4ef246be7117acf164c85b7316d0fbf17f3b08b256`/
`ca196505690a1b744bba2e2d689d751f454d30fb0f97856ce4d43587201380fd`/
`40fdb668b21a5d9392df1bfd32a2603e76d01be2d3c44ef11d8d11c38f032eda`/
`e4e1a684bf22fed455be9ff6d57d5fd7990c3616e8bd7db99d42a5a7e64fbcf9`。focused为
`8 passed in 6.54s`，连同fetch/prepare回归为`37 passed in 46.92s`。

本节只关闭`google_pdu17_multiday_unfiltered_cpu_power_capacity_alignment_available=true`。population
completeness、quality eligibility、absolute MW、真实flexibility/deadline/recovery/budget、continuous model、
formal result、paper claim和security certification gates保持false。

## 13. 统一公开数据交付中的 Google 边界

`rq2_public_data_delivery_v1_non_authoritative`把第10–12节的Google全57域power、PDU17 capacity和744小时
同钟pair纳入统一catalog，并生成744行流式可读的`google_pdu17_hourly_flat.jsonl.gz`及31个raw-origin
24小时block索引。扁平视图只是既有pair的确定性投影：CPU端点与14个strata、12点power均值和原flag计数、
capacity unknown均保留；没有计算CPU/capacity比、MW、headroom、flexibility或恢复参数，也没有选择自然日、
train/holdout或跨来源coupling。

2026-09-12复核时，官方master与已锁commit `3f6a61...`中的PowerData PDF/notebook仍与本地已审版本逐字节
一致：PDF SHA-256为`06011d9dd34b7649944f092b2b15fdd83976a6be3d7e358c128ef49666f90743`，notebook
SHA-256为`437d63229469d8525ffbf6e57603cd1667502a2a3f6beadc7f3d05e34c1dccc2`。有限的官方repo检索未发现
解除两者flag方向冲突的勘误；这不是对全部issue/history的穷尽证明。因此`bad_*`仍作为observed diagnostic
值原样保留，过滤规则继续是unidentified/unregistered，不能以字段名、比例或本交付状态推定方向。

统一交付的summary SHA-256为
`53b898e30d807b3b532cfaed78de20fdb0653fa53817f65fcc5a6a5d78483586`，Google扁平表与block索引SHA-256分别为
`a319d9af7691b8a4bc161dc005f405678b659b106b807edd4301b12187969101`/
`7737508894dc2cb0cc320e3d796d9e1ef9ec7f45101cb4960bc3aaf130b6f3c3`。本节只关闭本地catalog、离线校验、
流式读取和既有unfiltered alignment的交付门；quality、population、absolute MW、deadline、recovery、budget、
continuous model、formal/result/claim/security gates均保持false。
