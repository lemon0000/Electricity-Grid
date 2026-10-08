# 连续多日服务参数证据表 v1

状态：`DRAFT_NONAUTHORITATIVE`；依据2026-09-12本地已核验交付包，未新增外部检索或参数标定。
证据入口：`data/processed/rq2_public_data_delivery_v1_non_authoritative/catalog.json`、`data_dictionary.json`、`input_status.json`。
交付summary SHA-256：`53b898e30d807b3b532cfaed78de20fdb0653fa53817f65fcc5a6a5d78483586`。
字段的evidence_class与role分开：identifier/diagnostic不自动属于真实观测。

## 可用证据及适用边界

| 参数/数据 | 证据类别与本地dataset ID | 可支持 | 不能识别 |
|---|---|---|---|
| PDU measured power ratio | observed source；google_power_57_domains | 归一化功率原值/原flag | absolute MW；flag质量合格性 |
| 744h CPU端点、功率小时均值、capacity积分 | derived from observed；google_pdu17_744h_pair | 同钟连续小时描述；unknown/conflict保留 | 完整PDU人口；headroom；柔性 |
| Alibaba release/completion envelope | derived execution proxy；alibaba_job_execution_envelopes | 匿名执行轨迹 | deadline、checkpoint-safe recoverability |
| Alibaba workload blocks | derived normalized marginal；alibaba_dimensionless_workload_blocks_v3 | 既有split内连续边缘；raw>1保留 | absolute power或观测可调用比例 |
| RTS-GMLC CFE/outage blocks | derived benchmark；rts_gmlc_power_blocks_v4 | 电力侧时序与模拟事故身份 | dispatched grid need；经验联合分布 |
| Zeus/NLR/WattGPU设备测量 | controlled observation及派生表；zeus_four_gpu_power_performance / nlr_genai_power_profiles_v2 / wattgpu_power_reference_v1 | 设备级功耗与性能参考 | 跨数据源逐job功率映射 |
| Google DR/CICS本地摘要 | external operational evidence；data/raw/google_operational_flexibility_evidence_v1 | 已存网页中的调用窗口/系统设计背景 | 2019 cell-f或Alibaba逐job合同 |

## 尚未识别的20项参数

各项实证值均为null，直接依据交付`input_status.json#/unidentified`的同名记录及reason。
测试值来自YAML `synthetic_fixture`，属于机制假设，不写回数据交付为观测值。正式取值均待注册。
功率/能量分别使用同一基准下的normalized power / normalized power-hour。

| 参数 | 实证值 | 测试处理 | 正式证据需求 |
|---|---|---|---|
| `service_deadline` | null | null | 业务deadline合同，不能以实际完成时间代替 |
| `recovery_deadline` | null | null | due-time与债务age定义 |
| `shared_flexibility_budget` | null | 累计energy=1.0 | 会计期与共享预算合同 |
| `recovery_headroom` | null | business=0.5，再取CFE surplus之min | 业务恢复可用性 |
| `recovery_efficiency` | null | 0.8 | 恢复能量/服务量定义与测量 |
| `absolute_google_pdu_power_mw` | null | 未赋值 | PDU物理容量；normalized ratio不能给出MW |
| `observed_job_to_power_mapping` | null | 未赋值 | 同job身份、设备与共同clock |
| `flexible_fraction` | null | 未选；显式call_limit不代替识别比例 | 真实可调用业务比例 |
| `recoverable_fraction` | null | 未赋值 | checkpoint-safe业务可恢复性 |
| `checkpoint_state` | null | 未赋值 | checkpoint状态观测 |
| `preemptibility` | null | 未赋值 | 业务可抢占合同 |
| `response_time_limit` | null | 未赋值 | job级响应合同；公开调用窗口不足以识别 |
| `maximum_event_duration` | null | 3 hours | 最大持续调用合同 |
| `minimum_rest_time` | null | 2 hours | 事件间休息合同 |
| `event_count_limit` | null | 2 per synthetic period | 事件定义与计数周期 |
| `energy_debt_limit` | null | 1.0 | 恢复债务上限合同 |
| `accounting_period_id` | null | synthetic-48h-period | 业务期起止与预算归属 |
| `initial_recovery_debt_carry_in` | null | 零历史；或debt/energy=0.125、count=1、prior=true、rest=2h的完整历史 | 完整carry-in来源 |
| `maximum_recovery_power` | null | 0.5 | 可恢复功率容量 |
| `call_limit` | null | 0.5 | 实际可调用功率 |

同样未被观测识别的机制项：加法义务结算、调用时禁止恢复、单一nonrolling period、显式初始状态。
合成baseline=1.0、grid/cfe各0.125、恢复0.3125、CFE surplus=0.5仅用于手算测试，不是标定结果。

## 六项协议选择的草案处理

| 未注册选择 | 本草案处理 |
|---|---|
| censoring_estimand | observed prefix状态与完整completion分开；缺deadline则后者undefined |
| tail_handling | null；未来真实新义务须保留 |
| delivery_new_split | null；旧split保持，跨split拒绝延续 |
| cross_source_coupling | null；不得由两条连续边缘推出经验joint |
| raw_workload_fraction_above_one_mapping | null；源值不clip，当前[0,1]回放接口不接该原始字段 |
| deadline_and_recovery_accounting | 单一nonrolling period的机制草案；deadline仍null，多period未支持 |

这些是待注册设计项，未关闭交付包内任何科学门。以上为早期multiday回放器的范围；后续机制实现与正式参数登记须按下表分别核对，不能再由这段历史说明推断当前代码缺失。

## 2026-09-28 当前参数登记入口核对

本节只定位现有实现和待补证据，不选择正式数值或改变研究对象。20项实证值继续以交付input_status.json为准；六项协议选择仍未注册。fixture中的数值不是正式默认值，代码接受一个字段也不等于该字段已有经验来源。

代码位置均相对于src/rq2_joint_deliverability_boundary_v1/。

| 未识别输入 | 当前实现入口或能力边界 | 登记时必须补齐 |
|---|---|---|
| `service_deadline` | `causal_policy.CurrentObservation.due_hour`只给新债务到期小时；不识别原始job的业务deadline | 区分业务完成期限与削减所生债务期限，不共用一个未说明的标签 |
| `recovery_deadline` | `debt_cohorts.DebtCohort`及`advance_debt_ledger`已有逐笔due-hour、逾期永久记录和右删失；known期限仅接受mechanism_assumption | birth到due的规则、端点时序、异质性与适用cohort；保持实证null |
| `shared_flexibility_budget` | `multiday.initialize_joint_replay`的`normalized_energy_budget`及共享账 | 数值、单位、会计期、四臂共同义务与B6独立规划账的区别 |
| `recovery_headroom` | `causal_policy.HourlyLimits.business_recovery_headroom`与`cfe_compatible_surplus`分别输入 | 两种上限的来源、尺度与逐小时可见性，不能把CFE surplus当业务能力 |
| `recovery_efficiency` | multiday envelope的`recovery_efficiency`；cohort按有效恢复工作量记账 | 效率取值及能量/工作量定义 |
| `absolute_google_pdu_power_mw` | 交付无PDU容量；机制MW基准不能识别Google绝对功率 | 若提出Google绝对MW结论须补实际容量；机制benchmark单独命名尺度 |
| `observed_job_to_power_mapping` | `workload_projection.project_workload_power`提供显式线性机制投影，不是逐job观测映射 | MW基准、精度、idle项处理及映射假设；保留observed_power_mapping=false |
| `flexible_fraction` | `capacity_policy.CapacityObservation.available_flexibility`接受显式可用量；不标定业务比例 | 从负载到可用柔性的规则、范围及训练前冻结身份 |
| `recoverable_fraction` | 聚合债务/恢复账不识别checkpoint-safe比例 | 机制可恢复性假设；经验解释需要独立业务证据 |
| `checkpoint_state` | 当前聚合机制没有逐job checkpoint状态输入 | 若研究逐job可恢复性须补状态；不能由聚合回放反推 |
| `preemptibility` | 部分响应和聚合调用不识别逐job可抢占性 | 业务适用集合与可抢占机制假设，或独立合同证据 |
| `response_time_limit` | `capacity_policy.CapacityPolicy.response_time_hours`与ramp共同限制当小时响应 | 小时模型中的响应近似、数值及解释边界；不是秒级动态安全验证 |
| `maximum_event_duration` | multiday envelope的`maximum_event_duration_hours`及跨chunk状态 | 数值、事件开始/结束定义和时间单位 |
| `minimum_rest_time` | multiday envelope的`minimum_recovery_hours`控制事件间休息 | 明确该字段是rest约束，不是债务偿还deadline |
| `event_count_limit` | multiday envelope的`maximum_event_count`与carry累计计数 | 数值及归属period，chunk边界不reset |
| `energy_debt_limit` | multiday envelope的`normalized_debt_limit` | 债务单位、上限及效率换算 |
| `accounting_period_id` | `DebtLedger.accounting_period_id`；跨period reset被拒绝 | 单一nonrolling期的起止；若选择rolling或多期，另补对应状态/实现 |
| `initial_recovery_debt_carry_in` | aggregate replay有完整carry检查；`initialize_capacity_policy`采用显式zero-history初始化 | 四臂初态来源；不得把aggregate非零小例当四臂/cohort非零初始化证据 |
| `maximum_recovery_power` | `HourlyLimits`及`CapacityPolicy.maximum_recovery_power` | 与业务headroom/CFE上限共同约束的取值、单位和来源 |
| `call_limit` | `HourlyLimits.call_limit`与capacity策略的显式容量/响应约束 | 当小时调用限额来源；不得等同训练得到的最小容量证书 |

此外，`CapacityPolicy.minimum_event_power`、`curtailment_ramp_per_hour`、`recovery_decimal_places`、`committed_capacity`和`capacity_declaration_id`均已有开发字段，但不属于交付20项未识别输入清单；正式协议仍须显式登记。committed_capacity的机制声明不能代替training capacity certificate。

### 六项选择与现有能力的边界

| 协议项 | 已有开发能力 | 尚需形成的正式内容 |
|---|---|---|
| `censoring_estimand` | cohort区分unknown deadline、逾期、按时偿还和末端删失；prefix/composite诊断保留停止状态 | 评分对象、事件、分母、权重、区间规则及完整服务与前缀证据的关系 |
| `tail_handling` | 观察末端保留债务，不补零尾、不自动清债 | 未来义务/continuation合同或上界未知的报告口径；不能承诺四臂均有有限完整容量 |
| `delivery_new_split` | 已有来源身份与同split连续窗口校验 | 正式窗口长度、stride、训练/holdout清单和重叠权重 |
| `cross_source_coupling` | 已有显式source-pair身份与适配 | benchmark coupling集合、选择规则及权重；不是经验联合分布 |
| `raw_workload_fraction_above_one_mapping` | `workload_projection`对raw>1返回unresolved并保留原值 | 超界映射合同及holdout处置；不得clip或因结果难处理而删除窗口 |
| `deadline_and_recovery_accounting` | 已有单期逐笔债务、due时点检查与跨日carry | deadline规则、period范围、恢复分配和初始化；多期/rolling选择依然需要相应实现 |

### 正常状态求解的独立前置

现有H25声明固定15秒求解；`normal_execution.NormalExecutionBudget`还限制单次最多30秒、normal累计最多60秒，gurobi_ordered内核直接复用该类型。外层`DeclaredTaskProcessBudget`未改变这两项限制。旧H25回放记录的`accepted_record_reproduced=false`、`optimality_certificate=null`仍有效。

因此下一项normal工作应是为实际规模准备显式数值预算后继及完整身份/回放绑定，保留旧预算和归档；不能仅改旧YAML的time_limit，也不能以外层wall变长宣布normal可用。先明确一次候选求解的预算与全部构模、赋值、witness、归档和独立回放成本，完成短测试/预审后才提交具体长任务。现有15秒结果不能保证延长后收敛，禁止通过放宽gap获得通过。

登记顺序：先把上述字段组织成自包含科学候选（取值、单位、机制身份、适用窗口、事件及删失分母），再对新增语义实现缺口逐项补齐；现有机制模块复用。20项实证null不是可随意补数的待办项，也不应与已有机制实现缺失混为一谈。正式接受机制benchmark及区间/unresolved结果仍按agent.md第7节单独审阅。
