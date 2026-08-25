# RQ2数据准备R3审查包

状态：`PASS`

独立`sol_reviewer`终审确认首轮provenance与测试覆盖问题均已关闭。本PASS仅
确认数据准备产物满足冻结验收标准，不授权正式实验或改变任何科学门禁。

## 原始请求

按重构后的RQ2架构识别、获取并处理后续实验所需数据，保留来源、许可证、
哈希、schema和fail-closed门禁，不覆盖已冻结70-cell结果，不启动正式求解。

## 验收标准

1. RTS-GMLC负荷、节点可再生和可靠性事件共享8,784小时时钟；
2. Alibaba PAI作业级执行包络不虚构deadline、checkpoint或恢复比例；
3. Alibaba实例遥测保留生命周期平均语义、缺失值和未知machine；
4. 实测/benchmark功率数据与PAI不伪造job或时钟配对；
5. CFE组合归属、事故经验性、SCOPF转换及正式实验授权保持关闭；
6. 每个原始源和处理包具有SHA-256与schema验证；
7. 相关测试、Ruff和依赖检查通过。

## 新增数据证据

| 数据包 | 关键规模 | Manifest SHA-256 |
|---|---:|---|
| `alibaba_job_execution_envelopes_v1` | 714,903 jobs | `73539a65c7db2b7cf630624048c00262a8e650a96b1412d21dcdf04ad857c219` |
| `alibaba_gpu_telemetry_v1` | 3,033,232 source rows；576,724 job×GPU rows | `908a3aec20a961bc8971f0944db3d18b33756021d7fedfa3c3d339a10aede51d` |
| `nlr_genai_power_profiles_v2` | 2,467 measured profiles | `1cef65fe087340a109e0e29ed604e991e9cdedca902017d639d99a59b8f2c677` |
| `wattgpu_power_reference_v1` | 4,798 experiments；8 GPUs | `fc5772007da61c0285368faf87b79c410f1f695c38fdbb99625eaceb79177446` |
| `rq2_joint_data_v1` | 8,784 h；24 buses；68 reliability components | `df6889870639e9f4b623c063c7e3fdf49bee671cf904489b3c69c4c05b0b5058` |
| `rts_gmlc_hourly_cfe_deficit_250mw_v2` | 8,784 h；与v1 CSV字节一致 | `cb6b941193db3a09cddb005c14f210bab754e5f9d12ba9c982f778b88409cc0a` |
| `rq2_data_readiness_v2` | 6 packages；5 source manifests；live provenance | `bc6eb20121868b5b25bfdceaa038f7c7045f28f5c9a57ced5721479ea2e4d749` |

## 需重点复核的不变量

- `direct_job_to_power_mapping_ready=false`；
- `flexibility_contract_parameters_ready=false`；
- `empirical_joint_distribution_ready=false`；
- `allocated_cfe_portfolio_ready=false`；
- `outage_to_grid_need_dispatch_ready=false`；
- `full_rq2_experiment_input_ready=false`；
- `formal_experiment_authorized=false`。

允许为真的新增中间门只有：

- `observed_gpu_utilization_covariate_ready=true`；
- `t4_hardware_overlap_power_reference_ready=true`。

## 已知数据质量事实

- Alibaba sensor有5,829个`cpu_usage`、1,217个`avg_mem`和各3个网络
  字段缺失；未填零；
- 9条sensor machine无法连接machine-spec，标为`UNMAPPED`；
- PAI sensor是实例生命周期平均值，跨实例统计为未加权均值；
- WattGPU有200行prompt/generation请求数组长度不一致；
- WattGPU有266行报告mean power与`energy/duration`偏差超过1%；
- NLR有200条online-rate profile被上游插值至`0.001 s`，不作为1 kHz
  独立测量；
- RTS-GMLC outage是可靠性参数抽样，不是观测事故或`grid_need_mw`。

## 验证证据

- 相关pytest：`49 passed`；
- provenance与关键不变量聚焦pytest：`19 passed`；
- 相关Ruff：通过；
- `pip check`：`No broken requirements found`；
- `git diff --check`：通过；
- WattGPU三项数据表二次重建字节哈希一致；
- Alibaba telemetry两项数据表二次重建字节哈希一致。

## 首轮REWORK处置

- CFE v1、冻结preregistration与70-cell结果保持未修改；
- 新增CFE v2，记录当前config、builder和derivation module SHA；
- 新增readiness v2，逐包核验live provenance；
- 跨包输入文件增加独立SHA约束；
- 高风险gate改为显式fail-closed；
- 测试扩展至全量8,784小时时钟键、714,903个envelope禁止字段及原始
  telemetry缺失/UNMAPPED审计。

## 审查输出要求

只读`sol_reviewer`应返回`PASS`、`REWORK`或`ESCALATE`，并优先检查：

1. 字段语义与统计聚合是否过度解释；
2. manifest是否覆盖所有声明来源；
3. readiness gate是否存在错误开启；
4. 测试是否真正覆盖不可变产物及科学边界；
5. 文档、配置和机器产物是否一致。
