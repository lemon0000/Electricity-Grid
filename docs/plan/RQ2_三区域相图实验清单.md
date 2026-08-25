# RQ2 三区域相图实验清单

## 1. 研究问题与科学价值

主问题不再预设 B6 必然更差，而是识别共享柔性系统的三个运行区域：

- `R1_no_conflict`：两类服务没有形成有后果的资源竞争；
- `R2_double_commitment_risk`：B6 的分离承诺导致容量低配或额外欠交付；
- `R3_common_insufficiency`：资源总体不足，correct 与 B6 的提交容量相同且均等价失败；若存在严格容量低配则归入R2。

该重构把阴性结果纳入理论对象，回答“重复承诺何时重要、何时不重要、何时被总体稀缺淹没”，而不是只寻找支持 H2 的参数点。

## 2. 研究设计与因果逻辑

### 已冻结主相面

| 维度 | 水平 | 作用 |
|---|---|---|
| 小时 CFE 目标 `alpha_hr` | 0.50, 0.70, 0.85, 1.00 | 改变 CFE scarcity |
| 网络压力阈值 | Google training q80/q90/q95/q99 | 改变网络调用频率 |
| 业务恢复 headroom | 20, 40, 80 MW | 改变债务清偿能力 |
| POI | Bus 8 | 主结果 |
| 网络口径 | minimum curtailment | 主结果 |
| 柔性预算上限 | 150 MW | 主结果 |
| seed | 20260822 | 主结果 |

主相面共48格。附加稳健性族覆盖：

- 三个seed；
- 80/150/250 MW预算；
- Bus 3/8/14/18；
- minimum-curtailment与overload-sensitivity两种网络口径。

去重后总计70格。完整设计见
`configs/rq2_three_region_phase_map_preregistration_v1.yaml`。

### 恢复时段 CFE 闭环

恢复功率不再使用常数headroom直接豁免CFE约束。逐小时使用：

```text
cfe_recovery_headroom =
    max(attributed_cfe / alpha_hr - D_DC, 0)

effective_recovery_headroom =
    min(business_recovery_headroom, cfe_recovery_headroom)
```

核心窗口和恢复尾部都读取连续RTS-GMLC CFE数据。该处理防止将清洁电力缺口转移到尾部。

## 3. 方法与统计推断

- training与holdout按各自源时间轴50%切分，无源小时共享；
- Google压力与RTS-GMLC CFE仍按独立边缘窗口配对；
- 阈值只由Google training半段计算；
- 每个cell先在training上分别求correct/B6，再固定`D_flex`执行holdout；
- holdout统一使用真实共享时序包络；
- seed只检验窗口抽样稳定性，不作为IID样本；
- 不报告p值或经验事故概率；
- unresolved与方向冲突cell不进入三区域。

## 4. 结果与外推边界

必须报告：

1. 每格region；
2. correct/B6提交容量；
3. 两者失败概率与期望短缺；
4. 容量低配、失败率和短缺差值；
5. training/holdout网络-CFE重叠率；
6. 有效CFE恢复headroom；
7. POI和网络口径下的边界移动；
8. `diagnostic_mixed`与`unresolved`完整列表。

不得报告为：

- 现实事故发生概率；
- 真实合同违约概率；
- PPA/REC采购结果；
- full-N1或AC安全认证；
- 数据中心场址推荐。

## 5. 论文叙事与图表

基于冻结结果，主文只保留与已观察证据相符的图表：

1. Figure 1：分离合同与共享物理包络；
2. Figure 2：三区域定义及判定流程；
3. Figure 3：退化的`alpha_hr × network threshold`相图；
4. Figure 4：50个共同training不可行与19个等价holdout失败的分解；
5. Table I：模型、基线与信息结构；
6. Table II：区域判据和容差；
7. Table III：70-cell完整分类和唯一mixed cell；
8. Table IV：POI、预算、seed与网络口径敏感性。

不存在R1/R2，因此不绘制不存在区域的代表轨迹，也不声称观察到边界移动。

## 6. 审稿风险与失败模式

- 若70格全部为R1：只能说明当前benchmark未产生有后果的重叠；
- 若全部或几乎全部为R3：与总体CFE scarcity或恢复约束主导一致，但需约束归因后才能作因果解释；
- 若R2只出现在单一seed或单一POI：不能声称稳健；
- 若出现mixed：必须检查目标权重、容量方向和短缺统计，不能删除；
- 若出现unresolved：该cell不形成科学结论；
- 真实恢复参数、联合事故-CFE分布和AC认证仍是外部阻塞。

## 7. 完成标准与剩余清单

### 当前可完成

- [x] RTS-GMLC CFE deficit派生；
- [x] 恢复时段CFE-compatible headroom；
- [x] 三区域互斥判据与fail-closed状态；
- [x] 70-cell预注册配置；
- [x] R4独立代码与科学审查（执行前`PASS`）；
- [x] 执行70-cell本地benchmark；
- [x] 生成CSV、summary、manifest和相图；
- [x] 生成论文结果叙事与表格；
- [x] 更新blocker与TSG投稿判断。

### 冻结结果

- 70/70 cells发布，correctness gate通过；
- `R1_no_conflict=0`；
- `R2_double_commitment_risk=0`；
- `R3_common_insufficiency=69`；
- `diagnostic_mixed=1`；
- `unresolved=0`；
- 50格为correct/B6 training同时证明不可行；
- 19格为两策略共享holdout等价失败；
- 唯一mixed格中B6提交容量更高且期望短缺低1.01 MWh，不支持H2。

因此当前相图是退化的共同不足图，而不是完整的三区域边界。禁止在查看结果后改动已冻结网格以寻找R2。代表性R1/R2逐时轨迹因相应区域不存在而不可生成，这属于结果而不是缺失运行。

### 外部证据阻塞

- [ ] 真实数据中心可恢复比例、恢复效率、deadline与headroom；
- [ ] 同钟网络事故和业务/CFE联合观测；
- [ ] PPA/REC归属与属地可交付性数据；
- [ ] full-N1、工程接入设备和AC控制参数；
- [ ] 多真实场址复现。

外部阻塞项目不能由合成参数或更多求解次数替代，因此不属于本地代码任务的“完成”定义。

### 后继数据准备

- [x] Alibaba PAI官方归档下载、许可证/哈希校验与全表处理；
- [x] 714,903个job-level执行包络，保留release/completion和GPU-seconds代理；
- [x] 3,033,232条官方实例遥测及576,724个候选job×GPU利用率汇总；
- [x] RTS-GMLC Area 1的8,784小时节点负荷、节点可再生与三seed可靠性事件包；
- [x] NLR GenAI Power Profiles v2归档校验及2,467条H100实测node-power统计；
- [x] WattGPU固定commit的4,798条异构GPU inference功率实验及PAI硬件覆盖表；
- [x] 统一`rq2_data_readiness_v2`机器门禁，逐包核验live provenance。

这些数据解除的是可复现输入准备，不改变上面的冻结70-cell结果。WattGPU虽与PAI存在T4同型号覆盖，但不共享job、模型或时钟；NLR同样不与PAI配对，RTS-GMLC事故为可靠性参数抽样，CFE资源也尚未形成已分配合同组合。因此`t4_hardware_overlap_power_reference_ready=true`，但`direct_job_to_power_mapping_ready=false`、`empirical_joint_distribution_ready=false`和`full_rq2_experiment_input_ready=false`。
