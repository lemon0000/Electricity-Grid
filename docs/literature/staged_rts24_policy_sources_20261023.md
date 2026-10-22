# 当前公共后继的策略与数值接受规则来源

2026-10-23，DRAFT_NONAUTHORITATIVE / PRE_SEAL_AUDIT。本表补充[132叶配置来源登记](staged_rts24_parameter_provenance_v1.md)，只追溯下列12项已经存在的规则，不引入策略、参数或D/E设计。定义来自[A规格](../model_spec/staged_deliverability_minimum_spec_v1.md)、[连续后继规格](../model_spec/staged_rts24_causal_development_v1.md)和[方法章](../../paper/drafts/staged_deliverability_methods.md)；有效实现位置见下表。原配置、运行代码和方法正文保持字节，源码位置/AST范围及SHA见[静态观察](../../results/tables/staged_rts24_policy_source_audit_v1_non_authoritative/static_observation_01.json)。

“本文机制选择”表示原规格声明的评价规则，没有经验校准或策略最优性资格；“实现绑定”表示有效调用关系或固定身份约束；“数值接受协议”表示声明模型尺度下的开发数值门，不是工程容差或严格数学证明。数值来自YAML时仍以原登记为来源，不改称代码实测。

## 12项规则及有效消费位置

| ID | 既有规则、定义源与类别 | 有效实现及独立核对位置 | 所消费的既有配置与主张限制 |
|---|---|---|---|
| P01 | 三方法及有效路由。A§7、连续规格§连续转移；实现绑定 | [causal_v2](../../src/staged_rts24_causal_v2.py)定义prepare_hour/accept_hour/execution_summary，并由[causal_v1](../../src/staged_rts24_causal_v1.py)导入initialize_execution/propose_hour；[audit_v2](../../src/staged_rts24_causal_audit_v2.py):audit_execution重建前缀与动作 | public.methods与三源身份；v1同名prepare/accept/summary不是当前有效路由。词法定位不构成执行闭包证明 |
| P02 | 当前输入与合成事件。A§6、连续规格§连续转移；本文机制选择/信息边界 | [public core](../../src/staged_rts24_development_v1.py):observe读取当小时资源；[reference_requests](../../src/staged_rts24_reference_queries_v1.py)在固定事件区间用selected[0]，其他小时normal；propose_hour只取state/prepared | business时间/设备/任务/清洁、public.project/actual_event/contingencies。fixture含整条合成truth；其SHA或计划名不使未来事件成为当时可见信息。本次没有非干扰执行证明，D/E的scenario_truth/policy_observation/reveal_hour仍待定义 |
| P03 | 完整合同与实际路径双父点。连续规格§证据与数值口径、方法§4.1/6.1；本文机制选择/查询身份 | public core:hour_requests/bind：fault_firm_F和fault_raw_need锚normal_contract_C；reference_requests及causal_v2:prepare_hour：当前raw/recovery锚reference_base_P0；audit_v2重核实际路径父点/证据 | public.network、rights及当前工程frame。C=F+X父点和未响应P0父点不可换用。有效actual子集不物化完整139节点；C−raw不替代独立fault-F点 |
| P04 | 原始g先求、再核合法X。A§4.2、连续规格§连续转移第1项；本文机制选择 | causal_v2:prepare_hour保留evidence.raw.point.curtailment_mw对应的原始数值请求，核活动X、剩余能量、爬坡、持续/次数/休息；audit_v2独立重算 | public.actual_event、rights与X包络、连续X carry；不截raw到合法X，不把缺证据/未决变零。不以局部通过声称完整合同成立 |
| P05 | 网侧优先、两承诺独立加总。A§4.1、方法§5.1式18；本文机制选择 | causal_v1:propose_hour先grid_q=min(g/a,room)，再green_q=min(h/a,room−grid_q)；audit_v2独立重算两分配与服务余额 | business功耗/共享D/alpha及当期Y；一次物理取电改善不抵扣另一独立承诺。该合同选择不是经验双服务合同或最优策略 |
| P06 | 原始g+h=0才恢复、调用/恢复互斥、EDF。A§5、方法§5.1；本文机制选择/确定性平局规则 | causal_v1:propose_hour按(due_hour,created_hour)排序；audit_v2按(due,birth)重算；[debt_cohorts](../../src/rq2_joint_deliverability_boundary_v1/debt_cohorts.py):advance_debt_ledger拒绝同时新增与恢复 | business.deadline_lag、eta和已到达旧债务。每小时一个聚合批次，created_hour唯一即该实现的批次身份；不是任意多批次ID排序。即使实际q=0，只要原始请求为正也不转恢复 |
| P07 | 三种动作上限。A§7、方法§5.2；本文机制选择 | causal_v1:propose_hour；audit_v2独立q_limit/r_limit/allocations重构 | instantaneous只用当期D/可延期量；fixed/full还用连续业务预算，fixed恢复用预先固定R_fix，full加当期K、网络上端及Y。二者均用D/max_recovery/债务÷eta。R_fix/eta仍是原YAML机制值，不据目标结果挑选 |
| P08 | actual点先核、物理接受与服务结局分开。连续规格§连续转移第3–4项、方法§5.2；本文机制选择/状态语义 | causal_v2:accept_hour重新prepare/propose，核actual_P同P0父、meter与proposal P在TOL_MW内一致、reported curtailment为0及audit_point；audit_v2重核accepted/applied/carry | 当前动作、网络点和前缀状态；已知projection/connection排除可保留失败而无actual点。full仅从非阻塞行应用账本，阻塞行保存但停止；简化账本仅hypothetical。hourly_cfe与cfe_call_shortfall不阻塞full的物理前缀，始终保留在原始记录及full replay；是否进入method自身判断按P09过滤 |
| P09 | 方法判断与完整回放不同。A§7、方法§5.2/7；本文机制选择/报告语义 | causal_v2:execution_summary的instant/recovery_omissions/relevant_by_hour/method_ok/replay_ok；audit_v2重核原逐时flags及接受scope，但不独立实现这两个汇总过滤器 | 三方法同原始违规记录；确切过滤与null规则见下文。引用独立逐时audit不声称有第二个独立summary过滤oracle |
| P10 | 连续账本、期限小时末结算、晚恢复不擦逾期。A§5–6、方法§3.3/7；本文机制选择/账务协议 | causal_v2:accept_hour、causal_v1:initialize_execution；debt_cohorts:advance_debt_ledger/assess_debt_cohorts；audit_v2按小时独立重建到期快照与carry | first_hour、registration_end/observation_end、deadline_lag与事件预算。账本小时offset只是非负索引编码；阶段/工程投运不重置。primary与随访分开，覆盖不足或期限未观察不补完成 |
| P11 | 正则化经济父点目标。方法§4.1、[公共规格](../model_spec/staged_deliverability_rts24_development_v1.md)；本文机制选择/数值来源绑定 | public core:load_fixture/PointRequest/build_point_model和[点/经济审计](../../src/staged_rts24_audit_v1.py):audit_economic_base使用同一系数 | public.network.economic_regularization_quadratic=1e−8已在132叶登记；代码默认值/相等检查是guard。目标给原cost二次项加epsilon，不是原目标最优面上的严格字典序，更不是经验成本校准 |
| P12 | 选定数值接受门。连续规格§证据与数值口径；数值接受协议 | audit_v1:audit_point/audit_economic_base、[child_optimality](../../src/staged_rts24_child_optimality_v1.py):audit_child_lp、[numeric_interface](../../src/staged_rts24_numeric_interface_v1.py):import_snapshot | 下表四个代码常量是开发协议，经验资格不适用；与HiGHS选项、资源帽、严格bound/工程认证分开。这里只登记选定常量，不穷尽全部数值分支 |

## 方法汇总的确切过滤

instantaneous自身只保留七种code：grid_service_shortfall、cfe_call_shortfall、device_capacity、connection_capacity、actual_network_point、hourly_cfe、shared_flexibility。其他原始违规仍进入完整回放。

fixed_headroom通常保留全部code；仅在proposal.recovery>0的行，从自身判断排除六种真实恢复资源code：device_capacity、connection_capacity、network_projection_lower、network_projection_upper、actual_network_point、hourly_cfe。原始记录和完整回放仍保留它们。full_temporal自身不排除违规。

method_ok先要求无自身相关违规、not stopped；fixed/full还要求无已观察primary期限缺口。原可为true但覆盖不完整时变null；fixed/full的右删失也使原可true变null。instantaneous在覆盖完整时不因未来期限右删失而自动变null。full_replay_ok要求全逐时违规为空、无primary期限缺口、not stopped；原可为true但覆盖不完整或右删失时变null。已观察false不被覆盖不足改写为null。

full_temporal物理前缀的blocking集合则是全部违规去掉hourly_cfe与cfe_call_shortfall。该差别只允许继续跟踪服务失败，两类服务本身仍未兑现，完整回放仍保留其违规；fixed恢复行的hourly_cfe可按上述六项清单从自身判断排除。accepted、method_ok及full_replay_ok是三个不同判断。

## 选定数值协议

| 常量 | 固定值与消费 | 资格 |
|---|---|---|
| TOL_MW | 1e−6；点审计的MW残差，及transport row activity等对应数值门 | 原模型数值尺度下的绝对门；不是设备/线路可放宽量 |
| TOL_RAD | 1e−9 rad；参考角残差 | 开发数值门，不代表相角工程安全边界 |
| TOL_KKT | 1e−6；经济/child KKT残差及child绝对primal-dual gap、transport reduced-cost echo | 各残差沿声明模型及目标尺度比较，不声称不同量纲已统一成物理MW；不是rigorous optimality证书 |
| TOL_OBJECTIVE_ECHO | 1e−6目标单位；snapshot objective与导出目标重算的绝对差 | 单独transport echo门，不是最优性证明 |

## 核验与未完成范围

本次仅原文/源码阅读、所列symbol和常量的AST静态定位、引用与SHA核对及只读领域/独立审阅；没有执行策略、科学模型、solver、native或新普通测试。静态观察不是策略语义证明、完整数据流/环境封印、独立科学oracle或D/E的policy freeze。既有132叶登记四源原字节保持。

该12项清单补齐所声明范围的定义—有效实现—资格追溯，不声称穷尽所有代码选择、solver配置或辅助数值消费。[P1原合同](../plan/staged_deliverability_c_native_p1_contract_v1.md)继续管理原生选项/资源/停止；[D/E合同](../plan/staged_deliverability_de_evidence_fields_contract_v1.md)中的数值方案、选择、敏感性、冻结及留出保持未定义。公共g、139节点、完整反事实F/X时序、现实校准、C/D/E预算和P1授权仍需原证据与权限。
