# RQ2数据准备与门禁报告

现行机器门禁为`rq2_data_readiness_v2`。V1保留为不可变predecessor；CFE
provenance修订见`rq2_data_provenance_amendment_v2.md`。

## 1. 研究问题与科学价值

目标是为“网络条件服务与小时CFE服务共享同一业务柔性”建立可审计输入，
而不是通过数据拼接预设B6必然失败。现有数据足以构建公开benchmark和功率
尺度敏感性，尚不足以估计真实合同违约概率。

## 2. 研究设计与因果逻辑

六个输入包保持独立来源和证据等级：

| 输入包 | 可支持的角色 | 禁止的解释 |
|---|---|---|
| `alibaba_job_execution_envelopes_v1` | 作业到达、完成、GPU请求和GPU-seconds | deadline、checkpoint、可恢复比例、绝对功率 |
| `alibaba_gpu_telemetry_v1` | 实例生命周期平均GPU利用量、显存、CPU和I/O | 连续功率轨迹、逐时可调容量、瞬时爬坡 |
| `rq2_joint_data_v1` | RTS-GMLC同钟负荷、节点可再生、可靠性参数抽样事件 | 观测事故概率、事件发生即等于网络调用 |
| `nlr_genai_power_profiles_v2` | H100节点功率尺度和动态形状 | 与PAI作业直接配对、设施侧实测功率 |
| `wattgpu_power_reference_v1` | T4同型号GPU功率尺度及异构GPU敏感性 | PAI逐作业功率、训练任务功率、V100精确型号匹配 |
| `rts_gmlc_hourly_cfe_deficit_250mw_v2` | 系统mix归属的CFE scarcity benchmark | PPA/REC所有权或属地可交付性 |

## 3. 方法与统计推断

所有源和处理结果均由SHA-256锁定。NLR归档为catalog v2，大小
`1,070,866,623` bytes，SHA-256为
`dcad6de800fb565d850b163902e2eddae48aabd1ed1c7336f9a1cdaf3012f137`，
完整ZIP CRC通过。其2,467条实测Parquet逐条检查schema、有限非负功率、
严格递增等间隔时间轴及上游mean/peak一致性；8条DIPLOEE设施曲线另表保存
为合成证据。归档中200条online-rate profile被上游脚本插值到`0.001 s`，
低于论文声明的`0.1/0.2 s`测量分辨率，因此只能保留其功率尺度，不能把
1 kHz点解释为独立测量或用于高频ramp校准。

WattGPU固定commit `4e010359c167ac8c65b55aabd1aafbf765ae5d91`按
Apache-2.0许可证下载8个对象。处理器逐行审计4,798条LLM inference实验，
覆盖49个模型、8种实测GPU及24个GPU×场景组。Tesla T4与PAI的497台机器和
196,065条候选task形成同型号硬件参考；V100/V100M32因显存型号和form
factor未完整对齐，不记为精确匹配。源数据中200行prompt/generation请求
数组长度不一致，266行`gpu_energy / measurement_duration`与报告mean
power相差超过1%；两类状态均保留，禁止静默修补。

Alibaba官方`pai_sensor_table`归档大小`406,119,947` bytes，压缩SHA-256为
`9a0b82e8bdf3949281e4ba1423d9b4b34847e52799eecb138966de46da69c7a0`，
解压成员SHA-256为
`12dd9929b70f3efe18d1279d9873e3a519c64f431613b23b059ed8c46a376dd7`。
3,033,232条记录中1,964,411条连接到完成候选，形成576,724个job×GPU
汇总；T4覆盖144,783个候选job。字段为实例生命周期平均值，
跨实例汇总为未加权均值；`gpu_wrk_util / 100`是GPU-equivalent
utilization而非功率。9条machine无法连接规格表，保持`UNMAPPED`。

## 4. 结果与外推边界

- Alibaba：732,318条候选task，714,903个job envelope；
- Alibaba telemetry：3,033,232条sensor记录、576,724个候选job×GPU汇总；
- RTS-GMLC：24个Area-1母线、27个可再生机组、68个可靠性component、
  8,784小时、3个固定seed；
- NLR：41条training、1,200条offline inference、1,026条finite online
  inference、200条rate-sweep profile，共11个工作负载/规模组；
- WattGPU：4,798条实验，其中T4 240条、V100-SXM2-32GB 525条；
- 统一门禁结论：
  `prepared_for_mapping_model_and_short_validation_only;formal_rq2_experiment_blocked`。

## 5. 学术写作与叙事

论文可表述为“公开作业轨迹、同型号T4功率参考、公开节点功率测量和公开
电网benchmark的分源证据链”。不得表述为单一数据中心的联合观测，也不得
把NLR H100或WattGPU inference功率系数直接赋给全部Alibaba任务。

## 6. 评审风险与失败模式

最高风险是跨数据集不可识别：不同硬件、业务和时钟使PAI到MW映射依赖模型
假设。其次是缺失deadline/checkpoint/recovery语义，以及把可靠性参数抽样
误写成经验事故。上述任一问题被忽略，TSG审稿人都可据此否定履约概率和
合同能力结论。

## 7. 改进路径

1. 预注册跨硬件功率映射模型，只把NLR范围作为外部尺度约束，并报告完整
   参数敏感性；
2. 获取或实验标定deadline、checkpoint、可恢复比例、恢复效率和headroom；
3. 将可靠性事件逐小时送入SCOPF，计算`grid_need_mw`，不得直接以停运计数
   替代网络调用；
4. 冻结可归属PPA/REC组合或继续明确采用系统mix benchmark；
5. 完成以上门禁后另建正式实验预注册，不覆盖现有70-cell阴性结果。

机器可读状态位于
`data/processed/model_inputs/rq2_data_readiness_v2/data_readiness.json`。
