# M6逐时网络-业务闭环数据契约

版本：`m6_business_chronology_v1` / `m6_incident_chronology_v1`  
状态：接口门与具名6小时/24小时benchmark耦合门已实现；完整M6外部证据门仍阻塞

## 1. 目的与边界

完整M6必须在同一连续时间轴上联合执行：数据中心业务负荷、可恢复柔性、事故轨迹、网络调用、业务恢复以及SCUC/SCED安全校核。M6a完成的是合成机制反例；另有具名原生RTS-GMLC 6小时归档和完整day-0 24小时公开benchmark完成了零柔性业务请求与逐时日前DC-SCUC/固定组合全状态ED的耦合。这些结果都不能用系统负荷代理业务负荷，不能把互斥N-1校核状态解释为事故频次，也不等于完整M6闭环。

本契约只解决“外部数据到来后如何无歧义、可审计地接入”的内部软件问题。它不生成缺失的真实数据，不把合成输入升级为观测证据，也不签发工程或合同认证。

## 2. 证据来源

每个输入必须携带以下来源元数据：

- `dataset_id`：稳定且非空的数据集标识；
- `source_kind`：`observed`、`published_benchmark`、`derived_benchmark`或`synthetic_sensitivity`之一；
- `citation`：DOI、正式数据页或可审计的项目内来源；
- `version`：数据版本或提取日期；
- `sha256`：所读CSV或恢复参数来源归档文件的内容哈希。

加载器逐文件重算SHA-256，来源、版本或内容漂移时直接失败。`synthetic_sensitivity`可以用于机制测试，但不能解除正式业务证据阻塞；`published_benchmark`或`derived_benchmark`可以支持测试系统结论，但不能表述为企业合同或场址观测；只有经审计的`observed`输入才可进入经验结果口径。

## 3. 业务时序CSV

列顺序必须严格为：

```text
timestamp,period,requested_demand_mw,flexible_demand_mw,recoverable_flexible_mw,physical_maximum_demand_mw,recovery_headroom_mw
```

字段含义：

| 字段 | 单位 | 含义 |
|---|---:|---|
| `timestamp` | ISO-8601 | 含UTC偏移的时间步起点 |
| `period` | - | 连续且不重复出现的规划期标签 |
| `requested_demand_mw` | MW | 未调用网络服务、未执行恢复时的电网侧业务需求 |
| `flexible_demand_mw` | MW | 当前小时物理上可调整的业务功率 |
| `recoverable_flexible_mw` | MW | 被削减后必须在后续恢复的柔性功率上限 |
| `physical_maximum_demand_mw` | MW | 设施、供电和业务共同允许的小时功率上限 |
| `recovery_headroom_mw` | MW | 基线以上可实际用于偿还业务债务的小时余量 |

硬校验为：

```text
0 <= recoverable_flexible_mw <= flexible_demand_mw
   <= requested_demand_mw <= physical_maximum_demand_mw
0 <= recovery_headroom_mw
   <= physical_maximum_demand_mw - requested_demand_mw
```

恢复功率上限和恢复效率作为带独立来源的`RecoveryParameters`输入；必须提供本地归档的`m6_recovery_parameters_v1` JSON参数记录并通过SHA-256复算，且代码中的两个数值必须与该记录逐项一致，不能只填一个未核验的摘要。效率必须在`(0,1]`。时间戳必须唯一、严格递增并按声明的`time_step_hours`连续。缺列、额外列、NaN、无穷值、负值、时间断点、重复时间或无UTC偏移均关闭门禁。

原始机柜、利用率、PUE或作业队列数据不能直接塞入本CSV。来源特定的预处理器应先生成并保留中间表，再映射为上述模型原生功率字段。

## 4. 事故时序CSV

列顺序必须严格为：

```text
event_id,start_timestamp,end_timestamp,kind,element_id,frequency_semantics,frequency_value
```

`kind`只能为`branch`或`generator`；起止时刻采用左闭右开区间并必须落在业务时钟边界上。当前M6只支持N-1，因此事故不能重叠。事故表只描述元件不可用状态，不预先指定削减MW；实际`grid_call_mw`必须由逐时网络调度结果给出，避免把假定调用量冒充电网结论。

频次语义只能是：

- `observed_occurrence`：每条观测事件的`frequency_value=1`；
- `sampled_from_published_rate`：按有来源的故障率抽样得到的benchmark事件；
- `scenario_weight`：明确的场景权重，范围为`(0,1]`；
- `deterministic_stress_no_frequency`：确定性压力见证，`frequency_value=0`。

`security_state_enumeration`不是合法频次语义。107个安全状态仍只表示互斥可行性检查。

来源等级与行语义也必须一致：`observed_occurrence`只能来自`observed`，故障率抽样只能来自`derived_benchmark`，确定性压力事件只能来自`synthetic_sensitivity`。不能给合成事件文件贴上`observed`标签来升级证据等级。

观测窗口内没有事故时，允许只含表头的空事故表；不得为了让模型运行而人工添加一次事故。该空表表示“此观测窗口记录到零次事件”，不是“元件故障率为零”。

## 5. 逐时调度接口

`src/grid/chronological_dispatch.py`定义完整时间窗接口，而不是逐小时无状态回调。请求必须同时包含：

- 连续时间戳和各母线既有系统负荷；
- 每小时机组可用状态；
- 数据中心POI、基线需求、可调用上限和恢复headroom；
- 事故轨迹；
- 初始开停机状态、初始出力和已处于当前状态的持续时间。

正式接入使用`build_chronological_dispatch_request`，不能由运行器重新手工拼接业务数组。该构造器直接读取已验证的`BusinessChronology`和`IncidentChronology`，计算`call_limit=min(合同调用上限, recoverable_flexible_mw)`，并把恢复headroom进一步限制在物理设施和已接入合同容量的共同余量内；恢复功率/效率必须与已锁定业务来源一致。`dispatch_result_to_flexibility_trace`再原样传递调度器的调用和恢复指令，供完整债务审计使用。

结果必须返回同一时间轴上的网络调用、恢复功率、数据中心实际功率、逐机组出力与开停机状态、系统负荷损失、网络损耗、机组组合/爬坡/备用标志、正常态与事故态安全标志、实际校核状态数及状态ID。验收器硬检查：

- 请求与结果时钟、长度和机组键完全一致；
- `grid_call_mw`不超过业务/合同共同上限；
- 恢复不超过业务、物理设施和已接入合同容量共同决定的小时headroom及恢复功率上限，且不与调用同小时重叠；
- `dc_power = requested_demand - grid_call + recovery`；
- `dc_power`不超过物理最大功率或已接入合同容量；
- 总发电等于既有系统负荷、数据中心实际功率与网络损耗之和；
- 不允许系统负荷损失；
- 不可用或停机机组不能发电；
- 每小时机组组合、爬坡、备用、正常态和所声明事故态均通过，且至少校核正常态和一个事故态；事故活动小时的`event_id`必须出现在该小时已校核状态ID中，不能只返回一个无身份的状态计数。

接口不自行声称已建成SCUC/SCED，也没有`security_certified`字段。只有真实求解器返回完整时间窗结果并通过验收后，实验运行器才可把`chronological_grid_dispatch_coupled`置为`true`。

当前满足该软件验收条件的正式实例为`rts_gmlc_google_day0_first6h_selected_n1_dc_scuc_v1`和`rts_gmlc_google_day0_full24h_selected_n1_dc_scuc_v1`。各自的`chronological_dispatch_request_built=true`和`chronological_grid_dispatch_coupled=true`只证明相应具名benchmark的请求已构造并由原生后端求解、验收；24小时实例关闭的是完整day-0计算规模门，这两个标志仍不得外推为真实业务恢复闭环、full-N1、工程级AC或安全认证。后续direct AC sensitivity不改变这两个调度接口标志的口径。

## 6. 恢复轨迹审计

`ChronologicalFlexibilityTrace.prescribed_recovery_power_mw`用于传入调度器实际选择的恢复功率。提供该字段时，包络评估器不得重新贪心安排恢复，而是逐小时审计：活动调用期间恢复、恢复功率越界、headroom越界、过度偿债、最大债务和期末债务。

每条轨迹还必须显式声明`boundary_state_status`。完整日历或经证据确认的清洁边界使用`clean_boundary_with_zero_carry_in`并强制所有传入状态为零；相邻窗口使用`linked_from_previous_window`，必须传入上一窗口的期末债务、末小时调用、活动事件累计时长、事件间休息时长、`has_prior_event`，以及同一统计期已发生的事件数和削减能量。若历史中已经发生过事件且链接点没有活动调用，必须给出明确的已休息小时，不能用`None`跳过最小休息检查；若历史从未发生事件，则`has_prior_event=false`且rest保持`None`，不能凭空制造休息状态。不能在窗口边界静默清零$q/on/rest$。轨迹还要显式给出`completed_periods`；轨迹内部发生标签切换的统计期自动视为完成，只有最后一个标签需要该集合声明，不能把期中分块的末小时误当成季度末，也不能通过漏填集合跳过真实季度边界。

未提供`prescribed_recovery_power_mw`时保留M6a原有的最早可行贪心恢复，只能作为独立业务包络见证，不能解释为网络-业务联合调度。

## 7. 现有可用数据与仍缺输入

官方RTS-GMLC `v0.2.3`已经提供73节点系统的8784小时负荷/风/PV/RTPV/水电/备用序列，以及机组爬坡、最小开停机、FOR/MTTF/MTTR和支路年故障率/平均持续时间。其完整day-0 24小时已经用于建立原生73节点benchmark SCUC/ED、六候选共同状态比较、两个代表POI的amendment-004 direct AC sensitivity及零数据中心normal AC对照/恢复诊断；故障率数据还可用于后续有固定随机种子的事故轨迹。

这些参数不能静默回填PYPOWER RTS-24：两套机组集合和Pmin不一致。基于故障率抽样的事故只能标记为`sampled_from_published_rate`，不能称为观测事故。

Google处理器已从55个可连接PDU构造744小时`observed_normalized_power_shape`：只使用通过测量质量标志的完整12点domain-hour，跨域作无容量权重均值/中位数，不插补、不求和。全窗峰值归一化只允许固定回放。独立shape builder把该形状映射为250 MW峰值、零柔性/零可恢复量的`derived_benchmark`；其中realized PDU power只是requested demand代理，250 MW只是项目假设而非观测容量。

独立day-0 builder使用同一PDU的24小时功率-NCU配对，但只按`measured_power_util_mean * 250 MW`直接缩放，不做day-0峰值再归一化，得到`172.770833333333-189.729166666667 MW`的派生需求。priority/NCU只进入候选审计表，不进入`flexible_demand_mw`、`recoverable_flexible_mw`或`recovery_headroom_mw`；这三个字段均为0。两份builder产物本身只表示`m6_business_chronology_v1`可加载，不提供真实绝对MW或真实柔性；day-0产物的前6小时及完整24小时均已由各自具名benchmark构造调度request并送入原生逐时后端。

### 7.1 具名原生RTS-GMLC day-0 benchmarks

两个正式实例均使用73个母线、158条机组记录、120条AC支路和1条`[-100, 100] MW`可控无损DC支路，其中73台常规机组参与组合。它们是日前selected-N-1 PWL DC-SCUC及固定组合全状态ED，不是实时SCED。6小时归档`rts_gmlc_google_day0_first6h_selected_n1_dc_scuc_v1`固定回放2020-01-01 00:00-05:00 UTC，派生需求范围为`172.770833333333-180.208333333333 MW`；24小时结果`rts_gmlc_google_day0_full24h_selected_n1_dc_scuc_v1`固定回放2020-01-01 00:00-23:00 UTC，覆盖完整day-0派生需求。

6小时实例每小时校核`normal`加11个预注册selected-N-1状态，关键支路为`A27`、`B22`、`C6`、`CB-1`，关键机组为`121_NUCLEAR_1`、`213_CC_3`、`313_CC_1`。2轮约束生成后，固定组合全状态ED目标为`157084.446540127 USD`，有效master下界为`157084.446540126 USD`，认证absolute gap为`1e-9 USD`、relative gap为0，已报告残差均为0。正式产物manifest SHA-256为`405c5109ef405f1961f6e9e461be5bfa42bd88f074bd30fa49e67006f6edcd10`。

24小时实例同样每小时校核12个状态，关键支路改为`A12-1`、`B22`、`C6`、`CA-1`，关键机组仍为上述三台。3轮约束生成后，固定组合全状态ED目标为`1193156.5322057535 USD`，有效active-master下界为`1193155.3829459916 USD`，认证absolute gap为`1.1492597619 USD`、relative gap为`9.632095e-7`，独立残差审计最大值约`1.4835e-9`。正式产物manifest SHA-256为`61b9d8c127354375769b5c1cf9e45e4340eafb0e89d8b07acbd8a08c9e1a0399`。

扩展时发现逐时custom commitment symmetry会删除物理上合法的crossing UC trajectories，故已将其移除；这是正确性修复，不是可选的性能设置。对二元开机状态逻辑等价的`reserve_up <= 10min_ramp * commitment`仍保留为精确LP凸包cut。正确模型的24小时normal master在118.9秒内达到zero gap，再进入上述selected-N-1约束生成与全状态ED复核。

两个实例的机组初值均由自由边界优化派生，状态为`optimization_derived_free_boundary_not_observed_chronology`，不是观测到的前序运行状态。6小时窗口只是day-0前段；24小时窗口虽覆盖完整day-0，但也不是已定义统计期末，二者均保持`completed_periods=[]`。因此只能证明各窗口内部的组合、最小开停机、爬坡和备用约束，不能补造窗口前运行历史或业务恢复统计结论。

事故CSV为空，只表示benchmark没有注入事故事件，不表示故障率为零。会导致孤岛的`B11`和`C11`被显式排除，故每小时12个互斥校核状态不是full N-1，也不能视为事故时序或频次样本。

资源口径将水电和RTPV固定到公开时序，将风电/PV作为可削减资源，并只包含regional Spin-Up，不含regulation或flex reserve；CSP、storage和同步调相机的有功功率被禁用。24小时结果只解除该具名公开软件benchmark的计算规模门。后续amendment-004 direct AC replay完整报告2304 case、2296收敛和0 direct-secure；零数据中心normal对照24/24收敛但0/24 secure，且官方电压边界内的560、565和三组IPOPT诊断均未见证h15/h21。它们没有full-N1或工程接入设备，也不提供观测绝对MW、真实柔性/恢复、观测同钟事故或工程证据。因此`treatment_followup_gate_passed=false`、`ac_security=false`、`security_certified=false`、`full_m6_model_input_ready=false`和`formal_vma_published=false`保持不变。

### 7.2 AC对照与treatment门

amendment-004修正同址在线Q-inert机组`VG`覆盖唯一Q-capable控制器源`VG`的初始化语义；amendment-003的`2276/2304`统计和manifest `2b5b705d...`只保留为invalidated parent diagnostic。正式结果为2296/2304收敛、0/2304 secure；收敛case中V/Q/支路/P违规分别为2296/2217/717/1470，manifest为`ee4894bba4e65433ffed4b31e4d96c78035bd2413dd4fa6accb3eb9f16c0609a`。

独立零注入控制重新优化无数据中心commitment，只覆盖24个normal小时，不是与treatment固定commitment、全状态逐case匹配的因果对照。其24/24收敛但0/24 secure，说明现有direct replay不能把违规直接归因于数据中心或POI。冻结PYPOWER 560的reference/distributed恢复分别为11/24和22/24，统一565为22/24；CasADi 3.7.2/IPOPT三组固定初值在官方`0.95-1.05 p.u.`边界内各为22/24，均未见证h15/h21。IPOPT返回`Infeasible_Problem_Detected`不是全局不可行证明；电压边界对称放宽`0.01 p.u.`后的24/24结果最高达到`1.06000001 p.u.`，只能作敏感性。

IPOPT canonical表为v2：零求解器调用、70个唯一字段、`scientific_outcomes_changed=false`，prereg/result manifest分别为`ffdf5d5df29101b463438cbf753e6b80b6babd31d74ea72df82c9648cf236ab3`和`75d40ffe53ded9747f916d57a3d00921d5087549afc8148cb2953f5924bf7332`；v1仅保留为superseded serialization。AC-aware commitment的`repair_005`已发布4/6个checkpoint后在candidate 5运行性中断，当前无solver进程；旧attempt不得resume，后续须使用新attempt ID和新output root重新取得lease。解除`treatment_followup_gate_passed=false`仍需完整发布并验证六个预算候选checkpoint、包含冻结父baseline的完整frontier、manifests、两阶段certificates、primary regret和final 24-state audit，再按冻结协议取得单一candidate/初值的24小时joint AC见证。另一条路径是取得有来源的tap、可切换shunt、补偿设备及控制参数。在此之前不得执行依赖零注入共同见证的treatment或升级论文结论。

AC-aware commitment首次v1 prereg在真实24小时pre-solver验证中暴露实现契约错误：`BUS_TYPE`会随commitment驱动的REF/电压控制器选择逐小时变化，不能作为跨小时静态网络字段。该v1没有candidate frontier或joint AC结果，失效manifest为`7ac6a6a2ecc76304376654b36d6a0e83e5bd506e9f3ff537356fa13ad94ac3dd`。v2 amendment只从静态相等字段中移除`BUS_TYPE`，并逐小时要求合法`PQ/PV/REF`与恰好一个`REF`；真实24小时preflight覆盖73台committable和72台reserve provider，但正式进程约`46725 s`后仍无checkpoint、frontier或joint AC调用，已停止且不得恢复。V3改用预注册的HiGHS 4线程exact-CG、动态实际界、solve期间30秒心跳、独立原生日志和预算候选原子checkpoint；其历史attempt及后续V4失败attempt均已停止且不得恢复，也不构成数学不可行或无解证据。最新`repair_005` attempt已在4/6个checkpoint后运行性中断；无frontier或joint AC，且该中断不是数学不可行或正式失败。

Alibaba处理器已全表审计并输出1,055,501个job、1,261,050个task、完整group/machine表、732,318条正GPU成功请求候选及1,642小时相对到达/资源请求。新增job-level执行包络覆盖714,903个job，以最早/最晚已终止任务时刻作为release/completion代理，并保存GPU请求量和GPU-seconds工作量。官方`pai_sensor_table`另提供3,033,232条实例生命周期平均遥测，其中1,964,411条连接到完成候选并聚合为576,724个job×GPU记录；`gpu_wrk_util / 100`只表示GPU-equivalent utilization。缺失值不填零，9条未知machine保持`UNMAPPED`，日期仍是匿名相对秒。Alibaba没有连续功率、checkpoint、deadline或恢复参数；Google与Alibaba来自不同系统且没有共同真实日历，不能拼成同一观测时序或把资源请求直接换成MW。

NLR GenAI Power Profiles catalog v2（DOI `10.7799/3025227`，CC BY 4.0）已按归档SHA-256 `dcad6de800fb565d850b163902e2eddae48aabd1ed1c7336f9a1cdaf3012f137`冻结。其2,467条实测profile来自每节点4张NVIDIA H100的Kestrel平台，处理产物保存source-defined CPU+GPU node-power统计；另8条DIPLOEE设施曲线明确隔离为合成数据。归档中200条online-rate profile被上游脚本插值到`0.001 s`，低于论文声明的`0.1/0.2 s`测量分辨率，不能作为1 kHz独立测量或高频ramp证据。该数据可约束功率尺度与低频动态形状敏感性，但与Alibaba PAI不共享作业、硬件或时钟，因此`direct_job_to_power_mapping_ready=false`，不能把PAI GPU请求直接换成MW。

WattGPU v1固定commit `4e010359c167ac8c65b55aabd1aafbf765ae5d91`提供4,798条LLM inference GPU功率实验。Tesla T4与PAI的497台T4机器、196,065条候选task形成同型号硬件参考，因此`t4_hardware_overlap_power_reference_ready=true`；但没有共享job、模型或时钟，且PAI含训练和未知任务，不能据此逐job赋值。V100/V100M32与WattGPU的V100-SXM2-32GB只作非精确架构参考，P100/MISC无覆盖。源数据200行请求数组长度不一致、266行报告mean与`energy/duration`偏差超过1%，下游必须并列保留报告值和重算值。

仓库仍缺有来源的配对绝对功率与业务工作量、柔性/可恢复比例、真实恢复headroom/效率/功率、同钟观测事故，以及候选扩建与数据中心接入的AC工程参数和控制证据。统一机器门禁见`data/processed/model_inputs/rq2_data_readiness_v2/data_readiness.json`，当前`full_rq2_experiment_input_ready=false`。CFE v1和readiness v1保留为冻结predecessor，现行provenance successor及修订理由见`docs/model_spec/rq2_data_provenance_amendment_v2.md`。zero-control与恢复诊断不能补齐这些输入；在软件benchmark层还需由`repair_005`的后继新attempt完成并验证六个预算checkpoint、包含冻结父baseline的完整frontier、manifests、两阶段certificates、primary regret和final 24-state audit，再运行后续joint AC，才能重新检验官方边界内的24小时共同见证门。

Mukherjee等1534条州级报告已冻结候选键、重复聚合、时长及失负荷队列。处理结果为1521候选组；主持续队列1385组/1398源行，另有已知失负荷和正失负荷敏感性。源行和candidate source IDs保留，重复严重度不求和。该预注册仍不证明候选组是独立物理事故，也不能估计事故频次或无条件时长分布。记录只定位到州/NERC区域，没有branch/generator资产ID、网络拓扑或SCUC/SCED；不得伪造RTS `component_id`或标成RTS `observed_occurrence`。

因此当前正式状态保持：

```text
benchmark_id=rts_gmlc_google_day0_full24h_selected_n1_dc_scuc_v1
benchmark_hours=24
chronological_input_interface_ready=true
absolute_power_mw_available=false
flexibility_observed=false
full_m6_model_input_ready=false
chronological_dispatch_request_built=true
chronological_grid_dispatch_coupled=true
full_n_minus_one=false
real_time_sced=false
ac_security=false
security_certified=false
formal_vma_published=false
```

其中两个`chronological_*`真值只属于上述具名6小时和24小时benchmark；24小时计算规模已在该公开软件范围内解除，但完整M6、工程安全认证、`security_certified`和正式VMA均未据此完成。
