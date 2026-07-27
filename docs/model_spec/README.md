# 模型规格总览

版本：0.4  
更新日期：2026-07-26
状态：L0/M1电网安全基础、L1确定性季度扩建MVP、L2固定策略F/X网络门、M4 B0-B2基线、M5a/M5b B3-B5场景树机制、M5c固定政策合成holdout、M6a连续包络和M6b逐时接口门均已实现；原生RTS-GMLC完整day-0 24小时selected-N-1 DC SCUC/ED、六候选共同状态多POI比较、amendment-004 direct AC sensitivity及零数据中心AC对照/恢复诊断已完成。AC-aware commitment的`repair_005` formal attempt已发布4/6个prefix checkpoint，随后在candidate 5 cost normalization中断；`operational_interruption` manifest为`66fd455aa958c06c809f9a51a5a9588a932843b83b2cd2953b9982bd1bdb057b`，active lease作为stale evidence保留，旧attempt不得resume，当前无solver进程。后续须以新attempt和新output root重新取得lease，并在六个预算checkpoint、完整frontier、manifests、两阶段certificates、primary regret和final 24-state audit全部发布验证后才允许joint AC。direct AC安全门为`0/2304`，零注入对照为`0/24` secure，官方电压边界内的24小时共同恢复见证仍缺h15/h21；上述机制和benchmark均非场址/合同证据，`treatment_followup_gate_passed=false`且`security_certified=false`；当前中断不能写成正式失败或不可行。

## 目标

本目录定义固定接入点大型AI智算中心的分阶段F/X接入、电网扩建、N-1运行、业务灵活性和清洁电力匹配模型。规格必须使另一名研究者无需猜测信息时序、单位或服务口径即可复现模型。

完整经济F/X参数识别和绿电规划仍处于规格阶段。当前代码已完成电网安全基础、确定性扩建MVP、固定F/X策略服务闭环、非经济B0-B2确定性基线、B3-B5合成多阶段机制与固定政策holdout，以及连续业务包络和逐时调度接口门；这些完成项不等于正式经验VMA或完整M6。代码实现仍按以下层级逐步启用：

| 层级 | 内容 | 进入条件 |
|---|---|---|
| L0 | RTS-24基础DC-OPF和关键N-1 | 基础潮流、功率平衡和线路限额测试通过 |
| L1 | 确定性季度扩建和固定数据中心 | 工程工期、投运状态和接入点容量测试通过 |
| L2 | F/X、服务闭环和T20/T50/T100 | F不可网络削减、X调用边界和容量块测试通过 |
| L3 | 两阶段与多阶段场景树 | 非预见性和单场景退化测试通过 |
| L4 | 持续时间、事件次数和恢复债务 | 连续时间窗口及期末债务测试通过 |
| L5 | 年度匹配、小时级CFE和共享预算 | 年度能量、逐时归属和重复承诺测试通过 |

当前实现边界：L0及其M1安全增强、L1确定性MVP、L2固定策略机制门、M4确定性B0-B2、L3的M5a/M5b与M5c合成场景外执行，以及L4的M6a/M6b接口门已完成；L5尚未实现。L1只支持确定性非下降季度需求、固定POI、firm-only、固定在线机组和一个捆绑的既有支路热增容工程。L2恢复F/X合同、实际服务和合同反事实三种口径，但F/X与开工计划是预先固定的合成政策，不是优化结果。M4-M5按词典序报告物理缺口、合同容量和X暴露的集合值端点，没有识别firm/X价格或唯一经济拆分。M5c只是在冻结合成holdout上执行既定B3/B4政策，不是经验VMA。连续包络已经独立检查响应、持续时间、事件数、累计能量、恢复债务和恢复功率，但尚未与有真实柔性和观测事故的逐时网络轨迹耦合，因此只达到L4机制/接口测试而不是完整L4运行验证。107个RTS-24联合状态不包含导致非计划孤岛的branch 10。

L1冻结算例的POI为bus 8，捆绑增容branch 11/12，工期2季度。四季度共428个状态-季度通过DC节点平衡、热限、故障元件零出力/零潮流和纠正边界审计。所有POI、工期、增容量和成本输入均标记为`synthetic_benchmark_not_site_evidence`；成本只使用未校准基准年的合成目标单位。当前`connected_capacity_mw`严格受当季需求约束且直接作为POI firm负荷，应解释为“已接入且正在运行的firm需求”，不能用于计算unused MW-year或替代M3合同容量校核。

L2冻结政策为`F/X=50/0,50/0,175/75,175/75 MW`。actual层按实际已接入需求运行，contract-counterfactual层在相同外生负荷、工程和事故状态下独立选择完整合同反事实调度；后者不是从actual当前调度瞬时迁移的保证。856个状态行和28248个逐机组行通过模型审计。静态门的连续验证小时现固定为0，不再由重复条件声明释放T。独立8784小时压力轨迹表明，满250 MW合同基线没有恢复头寸，q3/q4的X调用后债务不能按季度归零；因此连续机制敏感性只认定`50/50/175/175 MW`，得到`T_module=T20=q1,T50=q3,T100=q4+`。该结果不是逐时网络或运行认证。

M4冻结RTS-24基线使用相同的 $(50,100,200,250)$ MW需求路径与安全集合。B0得到 $U=327600$ MWh、X暴露区间 $[0,0]$，$F=C=(0,0,200,250)$ MW；B1得到 $U=109200$ MWh、区间 $[0,0]$，$F=C=(50,50,200,250)$ MW；B2得到相同的 $U=109200$ MWh但区间为 $[0,549600]$ MWh，minimum-X显示端点与B1相同，maximum-X端点为 $F=(0,0,125,175)$ MW、$X=(50,50,75,75)$ MW。三个策略均在q1启动、q3投运。由于静态状态的连续验证小时为0，`T_module=T20=T50=T100=q4+`且`security_certified=false`。这些是`synthetic_non_engineering_baseline_gate`下的冻结数值基线，不是工程或场址证据；B2区间也不能解释为其中任一端点具有经济最优性。

M5a冻结树为四季度12叶递进全因子：六条共享q1且只使用50/100/200/250 MW里程碑的需求路径，乘工程基础工期额外0/1季度。q2前只揭示当前需求类，各类仍保留两个终端需求后继；q3前揭示外生交付环境；q4前才揭示终端需求。自然节点和B4规划决策组按`1/3/6/12`细化，B3全期同组，B5全期单叶且机器标记不可实施。规划决策组只约束`F/X/z_start`，不约束由自然历史派生的工程可用状态。M5a同时锁定`rts24_common_fair_inputs_v2`完整payload哈希并从当前M4配置与RTS-24安全状态重算，不能只比较签名ID。等权概率是平衡合成设计，不是经验频率。M5随机模型必须恢复允许暂未使用合同权的`Dconn=min(Dreq,C)`，并按期望U、总合同容量暴露区间、minimum-总容量面上的X暴露区间依次锁定，不能让无代价容量由求解器任意选取。

M5b已按上述规则完成B3/B4/B5各13项stage，B4相对B3的树内合成缺口改善为`128800 MWh`，B5与B4在该树上相同但保持不可实施。M5c在12条冻结holdout叶上执行B3/B4的minimum-X和maximum-X端点，48次执行全部通过；两端点的合成holdout适应性值均为`110400 MWh`，同时保留3条延期/低需求路径上B4劣化`22080-33120 MWh`的失败区域。概率和holdout均为平衡合成机制设计，不得称正式经验VMA。

当前认证阻塞项包括：RTS-24没有响应时间/爬坡证据，机组故障也没有单列响应前频率状态；branch 10孤岛尚无规划处置；M1候选补救和M2/L2/M4扩建的热额定值、MVA/无功、工期及成本缺少工程证据；连续包络参数、事故轨迹和业务恢复头寸均为合成敏感性；RTS-24固定全在线机组仍没有启动、最小开停机和跨时爬坡；RTS-24扩建/F/X尚无工程AC复核；M4只识别B2集合值区间，没有可识别的唯一经济最优拆分。原生RTS-GMLC direct AC与零注入对照均为0 secure，且560、565和三初值IPOPT在官方边界内都未见证h15/h21；`repair_005`已发布4/6个checkpoint后在candidate 5中断，旧attempt不得resume且当前无solver进程；后续须以新attempt和新output root完成全部candidate-generation门，才可取得单一candidate/初值的24小时joint AC见证。另一解除路径是取得有来源的tap、可切换shunt、补偿设备及控制参数；观测事故、full-N1和接入工程证据也仍缺失。逐项证据和解除条件见`blocker_register.md`。

## 文档结构

- `information_structure.md`：季度场景树、可见信息、决策时点和非预见性。
- `notation.md`：集合、参数、变量、单位和索引。
- `formulation.md`：确定性MVP及多阶段、灵活性、CFE和CVaR完整约束。
- `metrics_and_validation.md`：指标、基线、自动测试和阶段停止规则。
- `m6_chronological_data_contract.md`：完整M6业务/事故时序、证据来源和逐时调度接口门。
- `blocker_register.md`：当前问题、已验证边界和解除外部阻塞所需证据。

## 已固定的建模选择

1. 主规划中的数据中心只有一个固定POI，不把站址作为决策变量；六候选多POI已用于独立的范围性benchmark外部验证，但其成本排序和不可行结果不回填为主模型站址选择。
2. 长期不确定性使用季度自然场景树；各基线另有机器生成的规划决策等价组。`F/X/z_start`定义在决策组上，工程可用状态和运行变量定义在自然历史上，避免把B3的计划共享错误扩展到场景相关状态。
3. `F`沿路径不可下降；总接入权 `F+X` 沿路径不可下降；允许扩建投运后把部分 `X` 转为 `F`，因此不强制 `X` 单调。
4. 不设置U容量。尚未取得接入权的需求记为接入缺口 `u_access`，它是结果指标和损失变量，不是容量产品。
5. 候选工程只能启动一次。已启动工程不能取消，未启动工程可根据当前信息继续等待。工程容量仅在实际工期和延期结束后生效。
6. 正常状态和关键N-1热限额是硬约束；CVaR不能放松线路、变压器或POI安全限额。系统原有负荷不允许通过负荷损失维持模型可行。
7. `F`表示规定状态下不因网络拥塞主动削减的容量权利。`X`是可按合同触发的条件容量，必须满足响应时间、持续时间、事件次数、能量和恢复约束。
8. X默认采用纠正性调用：事故发生后在合同响应时间内削减。主模型表示响应后的安全状态；有短时应急额定值时，另做“响应前不削减X”的短时安全检查。缺少短时额定值时必须明确采用预防性调用，不能静默忽略响应过程。
9. 硬安全、系统原有负荷和已签约F/X履约不参与经济权衡；在该可行域内最小化扩建、接入延期、合同调用、业务损失和风险成本。正式经济实验预注册参数范围并补充epsilon约束Pareto审计。M4例外地使用“先最小U、再报告X最小/最大端点”的词典序物理基线；M5合成小树先报告总合同容量暴露区间，再在minimum-总容量面报告X区间。两者都明确标记为非经济规范化，不得与正式经济目标混用。
10. 恢复和事件约束只在连续代表周或连续压力窗口上证明。年度能量可使用窗口权重，但权重不能替代小时状态链接。
11. `y_CFE`仅表示同小时、规定地域内可归属且与网络运行同时可行的清洁电量，不表示电子物理流向。
12. 主模型不包含储能属性追踪、绿证交易、跨数据中心任务迁移、电价设计或强化学习。

## 需要由配置给出的数据选择

以下项目不是留给实现者自由发挥的模型歧义，必须在YAML配置和数据说明中显式给出：

- RTS-24中的固定POI及最终申请容量；
- 中期局部增容和长期永久扩建项目、额定工期及延期路径；
- 正常和关键N-1集合、短时及持续应急额定值；
- 机柜数量、激活率、IT利用率、额定功率密度和PUE路径；
- 业务刚性/柔性比例、响应时间、持续时间、事件次数、恢复功率和能量预算；
- 连续代表周或压力窗口及其年度权重；
- CFE允许归属的地域、清洁机组集合及年度/小时目标；
- 训练场景、场景外样本、随机种子和场景映射规则。

## 规格审计原则

- 每个变量只表达一个物理或合同含义。
- 每个功率变量单位为MW，每个能量/债务变量单位为MWh，成本按配置币种记录。
- 规划节点、短期场景、连续小时和事故状态索引不得混用。
- 任何允许少供电的变量都必须有明确分类：未接入、合同允许削减、永久业务损失或非合同服务违约。
- 任一模型变体删除约束时，必须在基线定义中列出删除项，不能以不同代码路径产生不可审计差异。

## RTS-GMLC数据与结果边界

- 数据固定为官方`v0.2.3`、commit `3ece0d3725c844056132393ee252b3083dd4eab4`，并通过SHA256清单校验。
- 当前入口验证73母线、158机组、120条AC支路和8784个连续日前小时。
- 具名24小时结果`rts_gmlc_google_day0_full24h_selected_n1_dc_scuc_v1`已达到`resolved for scoped public benchmark`：完整day-0每小时复核12个状态，关键支路为`A12-1/B22/C6/CA-1`，关键机组为`121_NUCLEAR_1/213_CC_3/313_CC_1`；3轮约束生成后固定组合全状态ED目标为`1193156.5322057535 USD`，有效master下界为`1193155.3829459916 USD`，absolute/relative gap为`1.1492597619 USD`/`9.632095e-7`，独立残差最大约`1.4835e-9`。正式manifest SHA-256为`61b9d8c127354375769b5c1cf9e45e4340eafb0e89d8b07acbd8a08c9e1a0399`。
- 六候选多POI比较统一使用每小时24个共同selected状态。bus 120/108/220/320在冻结DC模型下可行，bus 208/308经自由边界连续commitment LP前缀确认model-infeasible；bus 120是唯一证书分离的最低成本可行候选，bus 108保留为已见压力锚点。该结果不是全盲试验或工程选址，aggregate manifest为`85f157a5f14f73ffa851c8dc1bc263f67719d794a900101b987dcab3f21dac66`。
- bus 120/108的amendment-004 direct AC replay覆盖全部`24小时 x 24态 x 2 PF`共2304 case：2296收敛、8不收敛、0 direct-secure；收敛case中V/Q/支路/P违规分别为2296/2217/717/1470，最大non-slack PG偏差为0，DC1重构残差不超过`3e-9 MW`。amendment-003的`2276/2304`结果manifest `2b5b705d...`因同址Q-inert机组覆盖Q-capable控制器`VG`而降为invalidated parent；amendment-004正式manifest为`ee4894bba4e65433ffed4b31e4d96c78035bd2413dd4fa6accb3eb9f16c0609a`。结果只证明冻结的无Q-limit switching、无redispatch/restoration回放未通过，不证明POI或真实场址工程不可行。
- 零数据中心正常态对照24/24收敛但0/24 secure，24个小时均有V/Q违规，支路/P违规分别为11/10。因此现有direct replay不能支持数据中心或POI的因果归因。
- 官方`VMIN/VMAX=0.95/1.05`下，PYPOWER 560的reference/distributed模式分别见证11/24和22/24，565仍为22/24；CasADi 3.7.2/IPOPT三组固定初值各为22/24，均未见证h15/h21。电压上下限对称放宽`0.01 p.u.`才得到24/24，最高`VM=1.06000001 p.u.`，故只能作敏感性，不能替代官方边界或通过treatment gate。
- IPOPT canonical表为`rts_gmlc_google_day0_zero_dc_ac_ipopt_diagnostic_v2`；它以`solver_rerun_count=0`移除v1重复的`solver_objective_mw2`列，`scientific_outcomes_changed=false`。v2 prereg/result manifest分别为`ffdf5d5df29101b463438cbf753e6b80b6babd31d74ea72df82c9648cf236ab3`和`75d40ffe53ded9747f916d57a3d00921d5087549afc8148cb2953f5924bf7332`。
- AC-aware commitment v1在真实24小时pre-solver检查中因把逐小时`BUS_TYPE`误作跨小时静态字段而失效；它没有发布candidate frontier，joint AC调用数为0，invalidation manifest为`7ac6a6a2ecc76304376654b36d6a0e83e5bd506e9f3ff537356fa13ad94ac3dd`。v2只修正该验证，但正式进程约`46725 s`后仍无日志、checkpoint、frontier或joint AC调用，已按运行控制要求停止；termination manifest为`e8bcef7466a1dfa44e4c0a444eb297fbf7160cf1f7596485c86a6fd9984b799b`，停止不是不可行证据且v2不得恢复。
- Gurobi/CPLEX/Xpress均已安装并通过接口smoke test，但当前自动许可证容量不足；HiGHS 1.15.1是当前唯一正式合格引擎。冻结6小时、24状态的1/4/8线程重复benchmark按非目标值规则选择4线程，result manifest为`4b05c7d7fcbd8f64ddb9eb61d4ee15c571a7905d8ebd453ac19d07cbf56c63d1`。随后单体与exact-CG重复比较中，exact-CG以`54.057/54.502 s`两次通过最终24状态审计；单体两次到时限且认证区间宽度为`0.003796157`，因此机械选择exact-CG，result manifest为`82f1f0cb72d574b2054f193f6354383c5629bd30796b42a919323ef326c0d7e1`。
- 上述选择只表示预注册比较矩阵中的最快合格配置。正式首个proxy master在`2801.9 s`才找到incumbent，约5秒后zero gap；父baseline本来就是成本帽内且proxy为`0.24328147100424327`的已知可行点，但当前Pyomo `highs`接口不支持MIP start。这是非阻塞性能缺口，不影响可行域或最终证书；任何`appsi_highs`/native warm-start后继都必须先独立重复pilot并建立新预注册，不能修改V3。
- V3冻结每阶段实际`LB/UB/absolute gap/incumbent-relative gap`证书：目标相对gap为`1e-4`，最大相对接受值为`1e-3`，proxy另有`1e-3`绝对gap上限；动态变化的是实际界区间，不允许看结果后改阈值。正式资格只读取stage顶层incumbent-relative字段，嵌套certificate的通用relative/target字段只作辅助诊断。每轮筛查全部inactive state，未解析状态保守提升，最终必须通过24状态fixed-shared LP与残差审计；cost commitment还必须通过`stage1 gap + 1e-7 + 1e-6`和`0.0010011`双重primary proxy regret门。preregistration manifest为`01646721d15395668bf0079cb6fe218dc0625187d1fbf108c5db74e47ae33f88`，input contract为`af4a388d80c211611a8e1dad3861936decb7f3c3e2de3a422116c87c013d8aa0`。
- 历史正式attempt `formal_20260719T061959Z`在每次solve期间启用30秒durable JSONL心跳，每个HiGHS调用有独立原生日志；截至2026-07-19 14:32 +08，首个预算候选当时仍在第一轮proxy master，尚无incumbent、预算候选checkpoint、最终24状态审计或frontier。该attempt现已停止且不得恢复，停止不构成不可行证据。`repair_005`旧attempt已运行性中断且不得resume；后续新attempt必须原子发布并验证六个预算checkpoint、包含冻结父baseline的完整frontier、manifests、两阶段certificates、primary regret和final 24-state audit；此前禁止joint AC且门禁保持false。
- 6小时归档`rts_gmlc_google_day0_first6h_selected_n1_dc_scuc_v1`继续保留：固定组合ED目标为`157084.446540127 USD`，有效master下界为`157084.446540126 USD`，认证absolute gap为`1e-9 USD`、relative gap为0；manifest SHA-256为`405c5109ef405f1961f6e9e461be5bfa42bd88f074bd30fa49e67006f6edcd10`。
- 正确性修复已移除会删除合法crossing UC trajectories的逐时custom commitment symmetry；逻辑等价的`reserve_up <= 10min_ramp * commitment`保留为精确LP凸包cut。修复后的24小时normal master在118.9秒内达到zero gap。
- 24小时、多POI和上述AC诊断只解除具名公开软件benchmark的计算与诊断门；`treatment_followup_gate_passed=false`、`ac_security=false`、`security_certified=false`、`full_m6_model_input_ready=false`和`formal_vma_published=false`。派生功率仍不是观测绝对MW，priority/NCU仍不是观测柔性；真实柔性/恢复、观测事故、full-N1和工程级AC参数/控制阻塞均未解除。
- Area 1序列仅作为RTS-24同谱系负荷形状代理，四个快照不构成逐时安全认证，也尚未加入新能源。
- RTS-GMLC与PYPOWER RTS-24的机组集合只部分对应，禁止把前者的ramp字段直接回填后者。
- 四快照统一使用`single_snapshot_static_unit_selection`。共享二进制状态覆盖每个快照的全部107个建模状态，但不同快照之间不链接，因此不得称为时序SCUC。
- RTS-24四快照AC映射按各母线有功倍率同比缩放原始无功负荷，固定并联补偿不缩放；有功组合关闭正容量机组时保留generator 14同步调相功能，并按当前在线机组单机上/下调裕度重选REF。该独立路径的四个正常态均已恢复为AC安全，事故态仍待审计；不得与上述原生RTS-GMLC direct replay混为同一AC结论。

## 需求追踪

| 计划要求 | 规格位置 |
|---|---|
| 季度场景树和可见信息 | `information_structure.md` 第2-4节 |
| 非预见性约束 | `information_structure.md` 第5节 |
| 工程工期和延期 | `information_structure.md` 第6节；`formulation.md` 第4节 |
| IT负荷、激活率、功率密度和PUE | `formulation.md` 第2节 |
| F/X容量及服务分层 | `formulation.md` 第3、5、6节 |
| B0-B2确定性基线、词典序端点和冻结RTS结果 | `formulation.md` 第1.3节 |
| 正常和关键N-1 | `formulation.md` 第7-9节 |
| 合同容量独立可交付性 | `formulation.md` 第8节 |
| 网络削减和绿电移峰共享预算 | `formulation.md` 第10.1节 |
| 持续时间、事件、能量和恢复债务 | `formulation.md` 第10.2-10.3节 |
| 年度和小时级CFE | `formulation.md` 第11节 |
| 多阶段期望成本和CVaR | `formulation.md` 第12-14节 |
| T20/T50/T100及首个模块 | `metrics_and_validation.md` 第2节 |
| VMA、unused MW-year和重复承诺 | `metrics_and_validation.md` 第4-7节 |
| CFE与恢复指标 | `metrics_and_validation.md` 第8-9节 |
| B0-B6及消融 | `metrics_and_validation.md` 第10-11节 |
| 自动测试和编码门槛 | `metrics_and_validation.md` 第12-14节 |
