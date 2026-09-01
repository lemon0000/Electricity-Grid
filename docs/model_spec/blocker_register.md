# 当前问题与阶段门禁登记

本登记只回答两件事：当前代码和固定数据能够证明什么，以及还缺什么才能解除阻塞。`resolved`表示问题已由代码、测试或明确的研究口径闭环；`mechanism-only`表示结构已实现但参数仍是合成敏感性；`method-blocked`表示数据与诊断已到位，但注册的方法尚未形成后续结论所需的数值见证；`external-blocked`表示不能靠当前仓库诚实补齐；`compute-blocked`表示模型与数据入口已经存在，但当前计算资源尚未完成所声明规模的正式运行，不等于数学不可行或数据缺失。

## 状态总表

| 问题 | 状态 | 当前处置 | 对后续工作的约束 |
|---|---|---|---|
| F/X价值参数不足、唯一最优拆分不可识别 | resolved as set-valued rule | 不估计唯一经济最优；使用主目标最优面上的X暴露区间 | 可实现B0-B2机制比较，不得声称福利最优F/X |
| M3成本是PWL选点后的回算值 | resolved for direct numerical QP | 原始凸二次目标由OSQP直接求解，经原约束审计和HiGHS L1线性可行性投影后再最小化调用 | 变量移动与目标偏差包络只用于数值可行性验收，不是最优间隙或误差证书；可称直接数值QP结果，无对偶最优间隙时不得称数学精确全局最优 |
| M2有限启动选择的二次目标求解 | resolved for finite fixed-start enumeration | 完整枚举不启动及每个启动季度；各候选用OSQP直接数值求解原始凸QP并由HiGHS线性修复 | 可称完整枚举中的最佳已解析数值QP候选；无显式最优间隙证书时不得称数学精确全局最优，多工程扩展仍需可扩展方法 |
| M4 B0-B2公平机制门 | resolved for synthetic mechanism gate | 同一冻结输入、安全集合和集合值规则下，三政策各10项stage诊断及M3固定计划闭环全部通过 | 只解除后续模型开发门禁；AC、频率、branch 10、工程参数、逐时SCUC和真实恢复证据未闭环，`security_certified=false` |
| M5a B3-B5场景输入与信息结构 | resolved for synthetic structure gate | 冻结6条递进需求路径乘2个工程状态的12叶全因子、等权概率、分阶段揭示和B3/B4/B5规划决策组 | 只允许开始随机模型编码；不是经验概率或正式VMA，必须先解决合同权和集合值目标口径 |
| M5b B3-B5随机基线机制门 | resolved for in-tree synthetic mechanism gate | 精确实现`Dconn=min(Dreq,C)`、双层107态网络校核、13-stage集合值规则、自然节点运行副本与B5逐叶严格分解 | 可进入独立场景外策略执行；当前结果不是正式VMA，不得用B5作为可实施政策 |
| M5c B3/B4固定政策场景外门 | resolved for deterministic synthetic holdout | 冻结6条训练集外需求路径、历史映射和训练端点哈希；48次固定政策双层107态执行全部通过 | 可报告合成holdout适应性值及失败区域；无经验抽样分布和统计区间时不得称正式经验VMA |
| M6a F1-F3连续包络消融 | resolved for synthetic mechanism gate | 锁定M3网络调用证书；同一full-X轨迹下F1/F2通过、F3因恢复债务失败 | 证明MW-only会漏判恢复不可行；网络回放为零调用退化结果，不是合同或逐时网络认证 |
| M6b逐时证据输入与调度接口 | resolved for interface gate | 新增业务/事故/恢复参数实质哈希锁定、同钟/N-1验证器、证据到调度的类型化构造器、跨窗口状态链接及具名安全状态审计；具名6小时和24小时派生benchmark均通过该接口 | 只关闭内部接入歧义和两个具名公开benchmark的软件门；不解除外部证据或安全认证阻塞，`security_certified=false` |
| RQ2 `grid_need` 从 RTS-24 物理派生 | mechanism-only selected-N-1 DC bridge | 定义A逐状态最小化Bus 8削减并保持热限为硬约束；定义B用outage-topology POI PTDF折算过载；配置禁止手填`grid_need_mw`并保存逐状态provenance | 仅替代L5手填网络需求，不能解除响应时标、branch 10孤岛、full-N1、AC/无功或工程参数阻塞；概率仍非经验事故概率，`security_certified=false` |
| RQ2 L5共享时序包络 | mechanism-only chronological MIP | `chi=c_grid+c_green`共享事件、能量、恢复与债务状态；B6分离双包络后回放真实合计轨迹；持续时间/事件数/能量/恢复债务均在recourse内为硬约束 | 网络事件时点、恢复头寸和业务包络参数仍为合成敏感性；未形成经验履约概率或合同能力，`security_certified=false` |
| RQ2 H2时序场景外执行 | mechanism-only chronological source ablation | training先冻结correct/B6的`D_flex`，holdout只解正确共享recourse；manual/generated/reduced只改变training，使用同一SHA绑定holdout；后继green call由RTS-GMLC可再生出力/负荷比例派生 | Alibaba代理和RTS-GMLC CFE-deficit两版跨来源H2均为阴性；后者在当前100%小时目标下correct/B6的holdout服务失败率均为1，缺少辨识度，不能据此调参；仍无linked carry-in和经验事故/恢复分布，`security_certified=false` |
| RTS-GMLC 6小时selected-N-1 DC SCUC/ED | resolved for scoped public benchmark | `rts_gmlc_google_day0_first6h_selected_n1_dc_scuc_v1`完成2020-01-01 00:00-05:00 UTC六小时求解；每小时12个预注册状态含normal，2轮约束生成后全部状态复核；固定组合ED目标`157084.446540127 USD`，有效master下界`157084.446540126 USD`，认证absolute gap为`1e-9 USD`、relative gap为0；产物manifest SHA-256为`405c5109ef405f1961f6e9e461be5bfa42bd88f074bd30fa49e67006f6edcd10` | 仅该具名范围可置`chronological_dispatch_request_built=true`和`chronological_grid_dispatch_coupled=true`；初值为派生自由边界，事故表为空，`completed_periods`为空，且非实时、非完整N-1、非AC，`security_certified=false` |
| RTS-GMLC 24小时selected-N-1 DC SCUC/ED | resolved for scoped public benchmark | `rts_gmlc_google_day0_full24h_selected_n1_dc_scuc_v1`完成完整day-0 24小时求解；每小时12个预注册状态，关键支路`A12-1/B22/C6/CA-1`、关键机组`121_NUCLEAR_1/213_CC_3/313_CC_1`，3轮约束生成后全状态固定组合ED目标`1193156.5322057535 USD`，有效master下界`1193155.3829459916 USD`，absolute/relative gap为`1.1492597619 USD`/`9.632095e-7`，独立残差最大约`1.4835e-9`；产物manifest SHA-256为`61b9d8c127354375769b5c1cf9e45e4340eafb0e89d8b07acbd8a08c9e1a0399` | 只解除该具名公开软件benchmark的24小时计算规模门；不解除真实绝对MW、真实柔性/恢复、观测事故、full-N1、工程级AC或`security_certified`/正式VMA阻塞 |
| RTS-GMLC 六候选共同状态多POI比较 | resolved for scoped benchmark comparison | 机械候选`108/120/208/220/308/320`共同使用每小时24个selected状态；120/108/220/320可行，208/308在自由边界连续commitment LP前缀中model-infeasible；bus 120为唯一证书分离的最低成本可行候选；aggregate manifest为`85f157a5f14f73ffa851c8dc1bc263f67719d794a900101b987dcab3f21dac66` | bus 108是已见锚点，不能称六点全盲；模型不可行不是工程场址不可接入，最低DC成本也不是站址推荐 |
| RTS-GMLC 代表方案direct AC replay | resolved as amended diagnostic sensitivity; certification and treatment-followup gates failed | amendment-004批次完整报告2304 case，2296收敛、8不收敛、0 direct-secure；收敛case中V/Q/支路/P违规分别为2296/2217/717/1470；non-slack PG偏差为0，DC1残差不超过`3e-9 MW`；manifest为`ee4894bba4e65433ffed4b31e4d96c78035bd2413dd4fa6accb3eb9f16c0609a` | 只证明冻结的无补救direct PF未通过；已有零注入normal对照但不是逐case匹配因果对照，且无工程接入设备、真实Q/控制和full-N1，不能归因于POI或宣称工程不可行，`security_certified=false` |
| PYPOWER同址slack机组语义 | resolved by transparent amendment 003 | 首个完整批次因内部机组排序导致实际slack UID与报告UID不一致，父manifest `51ba90b...`已作废为诊断；003要求REF母线恰有一台在线committable机组并机械复现旧错误，corrected结果所有收敛case的non-slack PG偏差为0 | 父批次的全部outcome不得作为最终结论；固定`pypower==5.1.19`和`ENFORCE_Q_LIMS=0`，后续依赖升级必须重审语义 |
| PYPOWER同址Q控制初始化语义 | resolved by transparent amendment 004 | 发现同址在线Q-inert机组`VG`可覆盖唯一Q-capable控制器的源`VG`；004只允许把唯一Q-capable源`VG`复制到同址Q-inert行，并保持bus VM作为Newton初值 | amendment-003结果manifest `2b5b705d...`及`2276/2304`统计只作invalidated parent diagnostic；正式direct replay只使用004结果 |
| 零数据中心normal AC与共同恢复门 | method-blocked for treatment follow-up | direct control为24/24收敛、0/24 secure；560 reference/distributed为11/24和22/24，565为22/24，三组IPOPT原边界各22/24，均未见证h15/h21；`repair_005`已发布4/6 checkpoint，candidate 5在cost normalization中断，active lease为stale evidence但被保留，`operational_interruption` manifest为`66fd455aa958c06c809f9a51a5a9588a932843b83b2cd2953b9982bd1bdb057b`；当前无solver进程，历史attempt均不得恢复且不构成不可行证据 | `treatment_followup_gate_passed=false`；`repair_005_resume_allowed=false`，后续须新建attempt并重新取得lease；六个预算候选checkpoint、完整frontier、manifests、两阶段certificates、primary regret及final 24-state audit验证前，不得启动joint AC、依赖该对照的treatment或论文结果固定；另一解除路径是取得有来源的tap/shunt/补偿及控制参数 |
| V3两套relative-gap字段的解释 | resolved as authoritative-field separation | stage顶层按feasible incumbent归一的`target_attained/eligibility_status/maximum_acceptance`是唯一正式资格；嵌套certificate按`max(abs(LB),abs(UB),1)`归一的relative/target字段仅作通用辅助诊断 | 判断target是否达到时只读取stage顶层字段，不读取嵌套`certificate.target_gap_attained`；checkpoint仍须检查`certificate.valid`、maximum acceptance、final audit、primary regret和residual audit。论文不得引用嵌套target字段；未来后继schema应删除或显式重命名该冗余字段 |
| M6完整网络-业务时序闭环 | semantic-confirmatory pilot blocked | v5 HiGHS chain及202个checkpoint保留但停止且禁止formal resume；v6已实现E0、flexibility-underprovisioning、完整training-support、共同coupling、bootstrap和独立Gurobi目录；fresh v2环境与preflight通过，冻结v1 pilot完整回传但原比较器为`268/280 PASS`、`eligible=false`；observed-diagnostic semantic successor只完成纯读诊断且不改v1判决 | 先完成semantic successor独立R3审查，再建立并由用户授权fresh versioned confirmatory pilot；其完整manifest通过同一语义门及最终activation前，grid/pairwise/identification全部关闭 |
| RQ2 HiGHS同进程thread scheduler隔离 | R3 residual; formal authorization blocked | science测试单进程独立运行时10项通过；同进程先执行formal-batch首测后出现3项unresolved，符合HiGHS全局thread scheduler状态污染，不能解释为模型不可行 | pilot四阶段使用独立子进程且冻结threads=4，但正式授权前仍须完成针对性隔离诊断并证明进程边界消除该状态污染；本增量不改solver或thread语义 |
| RQ2 Vnext two-block pilot post-result evidence | V8 nonformal `committed_success`; `post_result_review_pending` | v8 唯一一次 fixed 0008→0009 run 已发布 result/PUBLISHED exact trees；public-only contract readback、Lamport signature、fresh PID/predecessor、HiGHS 1.15.1/4 threads、完整 6/39-sample resource journals 与无 seed tombstone 均机械通过。该运行结果不是 post-result verdict，也不追溯改写 v2 或 v7 | 下一门仅为独立 R4 post-result review；在其正式结论前不得开放 formal、论文 claim 或 security certification。`formal_execution_ready=false`、`claim=false`、`security_certified=false` |
| 真实重大停电事件分布 | processed candidate cohorts; independent-event calibration blocked | 已冻结1534源行、1521候选组及主/敏感性队列；主持续队列1385组/1398源行，重复组保留source IDs并以非缺失max/min而非求和审计 | 候选组不证明独立物理事故，仍不得估计事故频次或无条件时长分布；无资产ID、拓扑和SCUC，不得映射为RTS具名N-1或声称与业务同钟 |
| Google同系统工作负荷-功率配对 | resolved for one-PDU one-day normalized pairing | cell f/pdu17 day-0取得336格小时usage、1328条machine event和唯一audit；600秒偏移后形成24小时功率-NCU上下界、168行priority明细及可加载的零柔性`derived_benchmark`，全部SHA锁定 | 只解除“一PDU/一天/归一化功率/受限usage人口”和业务schema桥接缺口；不是绝对MW、完整PDU工作负荷、真实柔性或恢复证据 |
| ENTSO-E观测资产事故 | external-blocked on security token | 匿名API实测401，当前环境无令牌；页面批量导出同样要求登录 | 用户完成免费注册和REST API令牌申请前不执行；取得后仍不得把ENTSO资产ID映射为RTS ID |
| X只有MW上限 | mechanism-only | 新增连续轨迹包络，硬检查响应、持续时间、休息、事件数、MWh、债务、恢复功率和期末债务 | 合成参数不能解除合同认证阻塞 |
| T指标依赖声明的静态24小时 | resolved as evidence separation | 静态M3的连续验证小时改为0；另以8784小时时间轴输出显式压力轨迹里程碑 | 正式逐时运行T仍受时序电网和业务数据阻塞 |
| 50% Pmax响应与机组事故频率安全 | external-blocked | 继续标记合成灵敏度，机组持续事故不冒充响应前频率状态 | 不能签发运行安全或响应认证 |
| branch 10非计划孤岛 | external-blocked | 排除并作为失败单列；数学多岛平衡不视为处置证据 | 正式N-1认证受阻 |
| 扩建缺少AC工程参数 | external-blocked | 只报告DC MW机制结果 | 不能进行扩建AC认证或把MW增量写成MVA |
| 固定在线机组、无逐时新能源与跨时约束 | external-blocked on RTS-24 mapping | RTS-24仍只使用8784小时时间轴和Area 1负荷代理；独立原生RTS-GMLC已完成24小时benchmark | 原生24小时结果不能回填机组集合不同的RTS-24，也不能据此声称RTS-24逐时SCUC、可再生联合安全或运行认证 |
| PAI作业请求到绝对功率映射 | external-blocked for empirical MW claims; not required by dimensionless primary estimand | Alibaba已提供714,903个job执行包络及576,724个job×GPU生命周期平均遥测；NLR提供2,467条4×H100节点profile；WattGPU提供4,798条异构GPU inference实验，其中T4与PAI的497台机器/196,065条候选task同型号，但不共享job、模型或时钟，且V100型号未精确对齐 | `direct_job_to_power_mapping_ready=false`继续阻止Alibaba绝对MW与经验合同结论，但不阻止以`D_DC`归一化、把WattGPU/NLR仅作尺度外部检查的公开数据partial-identification主实验 |
| 真实业务恢复轨迹与恢复头寸缺失 | external-blocked | Alibaba job-level包络仍没有可恢复比例、checkpoint、preemptibility、真实恢复headroom/效率/功率或合同deadline；NLR功率profile也不提供这些调度语义 | 只能把作业类型和请求特征用于候选分层及预注册敏感性；不能签发持续容量、恢复或正式T指标认证 |
| Word研究方案中文编码损坏 | external-blocked on clean source or approved reconstruction | Git初始提交与当前DOCX均已把大量UTF-8中文误存为乱码并含不可逆`U+FFFD`；无干净历史版本，未用Markdown覆盖原19张表和格式 | 当前以可读Markdown执行计划和模型规格为准；论文冻结前需取得干净源文件，或经确认后从现有可读文档重建DOCX |

## RQ2 network-derived `grid_need` 机制门

新增 `src/grid/network_grid_need.py`，不修改 `scopf.py` 既有语义。两种口径均先固定正常态全数据中心负荷的最小成本DC-OPF调度，再施加相同纠正边界。定义A在每个选定 sustained N-1 状态下只允许削减POI数据中心负荷，保留节点平衡、故障元件退出、纠正再调度边界与支路热限为硬约束，并以最小削减为目标；场景需求取状态最大值。定义B在相同故障拓扑上计算Bus 8削减、Bus 13平衡的PTDF，将该灵敏度直接写入所有支路估算热限后最小化折算削减。B是诊断近似；正削减时保持`direct_physical_dispatch_witness=false`，不提供A的直接可行调度见证。

两线手算测试固定为80 MW POI负荷、两条40 MW并联线、单线故障，A与B均须返回40 MW。RTS-24回归使用0.8系统负荷、250 MW Bus 8负荷、37条非孤岛支路、32台正容量机组和0.5·Pmax纠正边界，A/B均得到36.8 MW且关键状态为`branch_11_sustained`；这仍不是正式批次或canonical结果。入口拒绝任何手填`grid_need_mw`，要求物理POI负荷与L5 `connected_demand_mw`一致，并将派生值送入既有L5的硬约束`c_grid >= grid_need`；B若估算削减超过POI负荷则保留估算值但禁止构造L5场景。逐状态审计覆盖节点平衡、热限、发电上下界、纠正边界、故障机组归零、潮流方程和削减边界。所有产物必须保留`derived`、`not_empirical_outage`和`security_certified=false`。

本门只移除了“`grid_need`完全手填”的结构性缺陷。0.5·Pmax仍是无响应时标的合成边界，branch 10继续因非计划孤岛被排除，且没有full-N1、逐时SCUC、AC电压/无功、接入设备和工程控制参数。因此不得把A/B结果解释为容量认证、真实事故概率或工程可行性。

## RQ2 L5时序recourse机制门

`src/models/economic_temporal_stochastic.py` 已把第10.2-10.3节约束放入优化而非事后筛查。正确模型只有一套物理状态；B6分别为网络、绿电维护两套状态，其模型内可行性仅代表错误签约逻辑。所有B6结果再以合计调用回放 `evaluate_chronological_flexibility`，由评估器按最早可恢复规则确定唯一共享恢复轨迹；该回放失败是预期待量化结果，不使求解器 gate 伪装成失败。

两类证据已固定：微型手算覆盖同小时重复承诺、最大持续时间、事件次数、累计能量、恢复债务，以及未完成终端债务的保留与报告；当前模型仍要求窗口起点为显式零carry-in，尚未实现跨窗口linked carry-in。8小时RTS-24机制算例使用合成单事件时点，A/B均派生`36.8 MW`，正确模型 provision `76.8 MW`，B6 provision `40 MW`，B6真实合计包络失败。该数值只证明机制链可运行；事件时点、恢复头寸、包络参数和单路径概率均非经验值，正式实验与统计外推仍阻塞。

## RQ2 H2时序场景外执行门

`src/evaluation/temporal_economic_holdout.py` 与 `experiments/run_rq2_h2_temporal_holdout.py` 已实现两阶段固定策略：先在training chronology上分别规划correct/B6的`D_flex`，两套计划都冻结后才开始任何holdout网络派生与recourse；每条holdout只求解正确共享包络。recourse不可行时另解green为零、`c_grid>=grid_need`且固定同一预算的mandatory-grid时序MIP，只有该诊断也证明不可行才计hard failure；固定下界轨迹审计只提供violation分类，solver unresolved不计为失败。未完成终端窗口保留并报告debt/state，right-censoring不计入失败概率。H2服务结论比较失败概率与短缺能量；恢复债务单列，不能以“少服务导致较低债务”抵消服务失败。

连续时序软件门已实现：`temporal_trace_scenario_generator.py`从training/holdout互斥时间段抽取完整小时窗口并追加合成恢复尾部；`temporal_scenario_reduction.py`按四个显式缩放分量的完整有序轨迹执行fast-forward，只重分配training概率且代表点保持为输入子集。`run_rq2_h2_temporal_source_ablation.py`在manual/generated/reduced三臂间固定同一份生成后SHA绑定的holdout，并原子发布arms、leaves、summary与manifest。旧二维均值场景仍不得升级为时序证据。

本机配置`rq2_h2_temporal_source_ablation_rts24_v3`的三臂和A/B网络口径均通过solver、unresolved和artifact correctness gate，但`h2_robust_across_sources=false`。冻结阈值`1.0`下共享holdout没有网络事件，manual臂在该holdout没有B6额外欠交付，generated/reduced两模型的提交量约同为`12.3244 MW`。该阴性结果证明当前trace-threshold敏感性不足以支持跨来源H2，不得以结果为依据事后改变阈值。后续若做阈值、窗口或种子敏感性，必须先冻结网格并完整报告失败区域。

后继`rq2_h2_temporal_cfe_source_ablation_rts24_v1`已删除generated/reduced中的Alibaba工作负荷代理，改用RTS-GMLC v0.2.3同小时`WIND/PV/RTPV/HYDRO/ROR`可用出力与系统负荷构造100%小时目标下的CFE deficit，再按模型单位换算为`green_call_mw`。为保持已冻结v1 runner字节不变，派生CSV同时保存`green_call_fraction=green_call_mw/D_DC`，旧runner以外部常数`1.0`和`green_call_scale_mw=D_DC`机械还原绝对MW，不重新归一化。8784小时派生调用范围为`0--244.07262873226085 MW`，均值`133.89189560828532 MW`，输入CSV SHA-256为`f1c483fdf20ccc1ddc8e484d719b51f5b67a497bd99fd9bd7347dc57518586a5`。本地三臂、A/B两口径均通过artifact gate，但`h2_robust_across_sources=false`：generated/reduced的correct与B6均承诺约`80 MW`，共享holdout服务失败率均为1，额外短缺约为0；manual臂B6相对correct多出`66.72768060856407 MWh`短缺。该结果说明100%目标与当前冻结包络形成普遍scarcity，导致两模型共同失败，不能作为B6差异的确认性证据，也不得事后降低目标或放宽包络追求阳性。

该CFE profile使用系统可再生比例作透明归属代理，不表示数据中心实际拥有PPA/REC或获得网络可交付的清洁电量。Google压力与RTS-GMLC CFE时序仍是独立benchmark边缘配对，不是同钟观测联合分布。旧Alibaba路径只保留历史结果复现；后续确认性设计如改变`alpha_hr`、恢复参数或窗口，必须先建立新的预注册，不得覆盖本地v1结果。

本门仍没有跨窗口linked carry-in、观测事故时点、真实恢复headroom或经验概率，不能报告经验履约失败率。Google压力阈值只是负荷形状触发器，不是故障发生模型；旧版Google/Alibaba和后继Google/RTS-GMLC都只允许作为独立边缘窗口配对。所有结果继续保持`security_certified=false`。

R4 temporal successor 已在
`configs/rq2_h2_temporal_successor_preregistration_v1.yaml` 冻结，但尚未
执行。确认性阈值只由 Google training 半段按 Type-7 q80/q90/q95/q99
机械计算；已观察过阴性结果的阈值 `1.0` 仅作为描述性边界复现。正式矩阵为
17 job，固定 8 小时 core、4 小时 recovery tail、200/60
training/holdout、3 个种子、A/B 两种网络口径和三种训练来源。当前
`formal_execution_ready=false`，`configs/experiment.yaml` 仍为
`pytest-smoke`。R4 独立审查已 PASS；剩余执行阻塞是用户另行明确授权和新的
不可变 `run-*` 标签。不得在看到 successor 结果后删除 cell、改变阈值或把
描述性 `1.0` 边界并入确认性结论。

## M4 B0-B2机制门验收

公平比较冻结为输入签名ID`rts24_b0_b2_common_inputs_v1`。规范化schema为`rts24_common_fair_inputs_v2`，当前完整payload的SHA-256为`76cda29db68705cc3f2ef5025f32d30ef07ceea62a552a97c45b01bf83287794`：三政策共同使用`50/100/200/250 MW`需求路径、`2184/2184/2208/2208 h`季度权重、0.8系统负荷倍率、相同bus 8 POI与两季度branch 11/12捆绑增容工程、排除branch 10后的同一107态安全集合、同一响应前/持续态额定值和纠正再调度边界。payload还覆盖算例来源版本、服务窗口口径、完整安全状态描述、目标和solver；任一公平输入漂移都会改变哈希。工程与服务参数均为合成机制参数，政策之间没有更换需求、安全状态或数值容差。

正式集合值结果为：B0主接入缺口`327600 MWh`、X区间`[0, 0] MWh`；B1主接入缺口`109200 MWh`、X区间`[0, 0] MWh`；B2主接入缺口`109200 MWh`、X区间`[0, 549600] MWh`。B2相对B1没有U优势，但其最小/最大X端点不同，因此拆分本身不可识别，不能用最小X展示端点冒充唯一经济方案。

三种政策各保存10项stage诊断并全部通过：7个求解stage为`ok/optimal`，3个审计stage为`ok/not_applicable`。端点原约束最大违约为B0 `9.88e-11`、B1/B2 `8.13e-11`，约为`1.00e-10`量级。每种政策固定计划后，M3 actual与contract-counterfactual各解析428个状态；最大功率平衡残差为B0 `5.74e-11 MW`、B1/B2 `3.05e-11 MW`。

M3主QP后的HiGHS L1线性可行性投影最大逐机组移动为B0 `3.35e-7 MW`、B1/B2 `1.96e-7 MW`，低于`1e-5 MW`门槛；主目标绝对偏差为B0 `0.0444`、B1/B2 `0.0368`合成单位，低于对应`5.53`和`5.01`数值验收包络。该包络是`numerical_feasibility_projection_envelopes_not_optimality_gap_or_error_certificate`，不是最优间隙或误差证书。

四个季度的`continuous_validation_hours`均为0，因此三政策的`T_module/T20/T50/T100`全部保留为`q4+`右删失。M4至此只完成合成DC机制门；代表性政策完整AC复核、响应/频率证据、branch 10保护与孤岛处置、扩建MVA/无功/电压/控制参数、逐时SCUC/SCED及真实业务恢复轨迹仍阻塞认证，所有正式输出必须保持`security_certified=false`。

## M5a B3-B5场景结构门

机器输入`configs/rts24_stochastic_baselines.yaml`冻结为`rts24_b3_b5_synthetic_tree_v1`，并强制重算上述v2公平输入签名；只保留相同ID但内容哈希不一致时校验失败。六条需求路径为`50/50/100/200`、`50/50/100/250`、`50/100/200/200`、`50/100/200/250`、`50/200/200/200`和`50/200/200/250 MW`；工程基础工期为2季度，外生交付环境增加0或1季度。两者完整交叉成12叶，需求路径权重`1/6`、工程状态权重`1/2`，每叶`1/12`。

该概率是`balanced_synthetic_factorial_mechanism_design_not_empirical_probability`。它用于不混杂的机制比较，不是达产或延期频率。q1自然树只有一个历史；q2前只揭示当前需求类，且每类仍保留两个q4终端需求后继；q3前揭示工程交付环境；q4前才揭示终端需求。自然节点数为`1/3/6/12`。B3的可控规划决策全期12叶同组，B4的规划决策组随自然历史按`1/3/6/12`细化，B5从q1起逐叶规划并以机器字段标记为不可实施。规划决策组只约束`F/X/z_start`；工程可用状态`v`由共享开工决策和各自然路径的Gamma派生，不得跨E0/E1强制相同。工程状态只解释为可在未开工时观察的外生审批、供应链或交付环境，不能冒充项目自身已发生的施工进度。

v2签名使用case标识、固定的`pypower==5.1.19`来源版本、派生机组/支路集合、107个完整安全状态及全部规划配置；它尚未逐项哈希底层bus/gen/branch原始数组。在当前锁定依赖且不允许本地修改site-package的环境中不阻塞M5a。若以后允许同版本本地补丁、替换case文件或供应链镜像，必须先把原始网络数组内容摘要纳入下一版schema。

M5模型实现前另发现一个必须封闭的口径问题：M4的`C+u_access=Dreq`禁止持有空闲合同权，不能用于需要跨需求叶预承诺容量的B3。M5必须恢复`Dconn=min(Dreq,C)`和独立合同反事实。只最小化期望接入缺口U时，总合同权仍可能无代价多释放，因此在`U=U*`面上必须先报告总合同容量暴露`E_C`的最小/最大端点；展示固定minimum-`E_C`后，再报告X暴露的最小/最大端点；所有物理端点锁定后才允许非经济工程规范化。随机模型、非预见性和退化一致性测试通过前，M5只标记为输入结构已冻结，不能报告正式VMA。

## M5b B3-B5随机基线机制门

M5b现已实现并正式复跑。每个策略都使用相同v2公共输入签名、12叶合成树、107个安全状态、actual与full-contract-counterfactual两层网络可行性，以及严格的`U -> E_C区间 -> minimum-E_C面上的E_X区间 -> 非经济工程规范化`顺序。三策略各13项stage全部接受，信息序`U_B5 <= U_B4 <= U_B3`通过，正式端点表已发布。

结果为：B3的`U=403200 MWh`、`E_C=[880800,880800] MWh`、minimum-`E_C`面上`E_X=[0,494400] MWh`；B4的`U=274400 MWh`、`E_C=[954400,1101600] MWh`、`E_X=[0,522000] MWh`；B5与B4的三个集合值结果相同，但保持`implementable=false`。B4相对B3的树内缺口改善为`128800 MWh`。端点最大原约束违约约为$1.85\times10^{-10}$，最大整数违约为0。

规模问题也已闭环而未削弱安全门：B3/B4把相同自然历史下的运行见证从48个叶-季度副本压缩为22个自然节点副本；B5利用完美信息下跨叶无规划耦合的可分性，逐叶解析并按原概率聚合完整词典序面。合成小系统上的分解/单体对照通过。正式运行约37.5分钟，没有删除任何安全状态。

本门只解除独立场景外评估的开发门禁。当前等权概率不是经验分布，B4等于B5只说明这棵冻结合成树上额外预见没有进一步降低树内U，不能外推为一般结论。正式VMA仍阻塞于预注册的训练/外样本生成与映射规则、固定策略执行器和禁止未来信息重优化的测试；完成这些之前不得把`128800 MWh`写成正式VMA。

## M5c B3/B4固定政策合成holdout门

M5c-a在查看holdout执行结果前冻结`rts24_b3_b4_synthetic_holdout_v1`：六条与训练需求路径完全不重合的递进路径为`50/60/120/210`、`50/70/160/240`、`50/90/170/210`、`50/125/220/240`、`50/175/205/215`和`50/225/250/275 MW`，与训练支持内的按期/延期1季度工程状态完整交叉为12叶。q2需求按`75/150 MW`阈值映射，等于阈值时进入上档；q3才允许使用实际工程状态；q4需求按`225 MW`阈值映射终端状态。q3需求不额外创造训练中不存在的分组。未来信息提前传入、B5映射、人工覆盖和训练端点SHA-256漂移都会关闭门禁。

M5c-b读取已冻结的B3/B4 minimum-X与maximum-X四套端点政策，只执行运行补救，不调用随机规划求解器。48次执行全部完成，每次均包含actual和full-contract-counterfactual各428个季度-安全状态。最大功率平衡残差低于`2.90e-8 MW`，firm与conditional合同违约均为0。

两种X端点的U结果相同：B3为`474780 MWh`，B4为`364380 MWh`，因此集合值合成holdout适应性区间退化为`[110400,110400] MWh`。这只说明当前物理U对两个已保存F/X拆分端点不敏感，不识别经济最优拆分。路径级结果不是普遍优势：B4在6条按期叶上改善`88320–331200 MWh`；在3条延期/upper叶上与B3相同；在3条延期/lower叶上劣化`22080–33120 MWh`。平均正收益由按期路径收益抵消延期低需求路径损失，必须同时报告失败区。

本门权重仍是平衡确定性设计，不是从真实达产/延期分布独立抽样，且尚无配对bootstrap或统计置信区间。因此可以报告`synthetic holdout adaptivity value`并回答机制条件，机器结果继续保持`formal_vma_published=false`；解除正式经验VMA阻塞仍需有来源的训练/测试分布、足够独立外样本及预注册统计区间。M6完整持续时间与恢复债务机制开发与该外部数据阻塞无依赖，可继续，但不得覆盖本门失败区。

## M6a F1-F3连续业务包络门

M6a使用SHA-256锁定的M3状态表和汇总作为网络调用来源。每个季度、actual/contract层取107态中bounded-response状态的最大minimum-call证书；所有值均为`0 MW`，与M3汇总的minimum-call总和0一致。因此`network_minimum_call_replay`在F1/F2/F3下全部通过是退化结果，只能证明当前冻结网络实例不触发X调用，不能证明完整业务包络无价值。

为检验约束本身，`full_x_contract_stress`在q3 actual/contract和q4 contract层各放置一次1小时`75 MW`调用，并保持相同轨迹做嵌套消融。F1只检查MW上限，F2再检查响应、ramp、1小时持续时间、休息、事件数和季度能量，二者均通过，q3/q4合格容量为`250 MW`且`T100=q3`。F3加入恢复功率、最大债务和季度末债务清零后失败：actual q3末债务`75 MWh`；合同层q3末`75 MWh`、q4末`150 MWh`。q3/q4合格容量降为`175 MW`，`T100=q4+`右删失。

该结果是一个严格的结构性反例：`call<=X`、时长、事件数和能量均通过，仍不能保证业务可恢复。它不提供事故频率、真实持续时间、恢复余量或合同参数证据。网络来源只耦合调用幅值，小时轨迹没有重新执行SCUC/SCED或AC安全，所以机器字段保持`chronological_grid_dispatch_coupled=false`和`security_certified=false`。

完整M6当前转为外部阻塞。解除条件是：有来源的数据中心小时工作负荷与可恢复比例、可用恢复headroom和恢复效率、事故起止/频次，以及同一时间轴上的机组组合、爬坡和网络校核。取得这些输入前不得把合成F3失败率货币化、概率化或签发容量合同，也不得推进依赖完整共享业务预算的正式小时CFE结论。

M6b已关闭内部数据接入和调度结果口径歧义。`m6_business_chronology_v1`严格校验带UTC偏移的连续时钟、业务功率层级和恢复headroom；恢复功率/效率必须与本地归档的`m6_recovery_parameters_v1` JSON逐项一致并通过SHA-256复算。`m6_incident_chronology_v1`严格区分观测事件、基于已发表故障率的抽样、场景权重与无频次压力见证，强制来源等级与行语义一致，并显式拒绝把安全状态枚举用作事件频率。类型化构造器进一步计算`call_limit=min(合同X上限,可恢复柔性)`和`headroom=min(业务headroom,物理余量,已接入合同余量)`，防止调用方绕过有来源的业务字段。

完整时间窗调度接口要求初始机组状态、业务包络、合同容量、跨时请求和逐时正常/N-1结果同钟返回，验收时硬检查服务平衡、系统功率平衡、零负荷损失、机组可用性、已接入容量、具名事故状态以及F2/F3包络。调度恢复指令与债务计算的有效恢复量分别保存，非法恢复不能清除后续债务。相邻窗口必须传入期末债务、末小时调用、活动事件时长、休息时长、同周期事件数和累计能量；只有显式列入`completed_periods`的真实统计期末才执行期末债务约束。相关契约见`m6_chronological_data_contract.md`。

该接口门不解除外部阻塞。仓库现有RTS-GMLC数据确有机组爬坡、最小开停机、FOR/MTTF/MTTR、支路年故障率/持续时间以及8784小时负荷/新能源序列；这些数据现已用于两个具名结果。6小时归档`rts_gmlc_google_day0_first6h_selected_n1_dc_scuc_v1`覆盖2020-01-01 00:00-05:00 UTC，每小时复核12个预注册状态（含normal），2轮约束生成后全部状态可行；固定组合ED目标为`157084.446540127 USD`，有效master下界为`157084.446540126 USD`，认证absolute gap为`1e-9 USD`且relative gap为0，manifest SHA-256为`405c5109ef405f1961f6e9e461be5bfa42bd88f074bd30fa49e67006f6edcd10`。

24小时正式结果`rts_gmlc_google_day0_full24h_selected_n1_dc_scuc_v1`覆盖2020-01-01 00:00-23:00 UTC。每小时复核normal加11个预注册selected-N-1状态，关键支路为`A12-1`、`B22`、`C6`、`CA-1`，关键机组仍为`121_NUCLEAR_1`、`213_CC_3`、`313_CC_1`。3轮约束生成后，固定组合全状态ED目标为`1193156.5322057535 USD`，有效active-master下界为`1193155.3829459916 USD`，认证absolute gap为`1.1492597619 USD`、relative gap为`9.632095e-7`，独立复算的最大残差约`1.4835e-9`；正式manifest SHA-256为`61b9d8c127354375769b5c1cf9e45e4340eafb0e89d8b07acbd8a08c9e1a0399`。

扩展过程中移除了会删除合法crossing UC trajectories的逐时custom commitment symmetry；这属于正确性修复，而非仅为加速。对二元开机状态逻辑等价的`reserve_up <= 10min_ramp * commitment`被保留为精确LP凸包cut。修复后的24小时normal master在118.9秒内以zero gap求解，随后才执行上述selected-N-1约束生成和全状态ED证书。

6小时和24小时运行都使用`optimization_derived_free_boundary_not_observed_chronology`初值、空事故表和空`completed_periods`，不提供观测初始运行历史、事故频率或完整统计期结论；二者都是day-ahead selected-N-1 DC SCUC/固定组合ED，不是实时SCED、full-N1或工程AC安全校核。24小时状态只解除该具名公开benchmark的计算规模门，不能解除真实绝对MW、真实业务与恢复证据、观测同钟事故、工程参数、`security_certified`或正式VMA阻塞。RTS-GMLC参数仍不能静默回填机组集合不同的PYPOWER RTS-24，基于故障率生成的事件也只能标记为benchmark抽样而非观测事故。

## RTS-GMLC多POI与直接AC诊断门

多POI候选不是手工看结果挑选：先从正负荷PQ母线按Area和138/230 kV分层，以相邻AC支路连续额定总和排序，在每个Area取138 kV中位点和230 kV最大点，得到`108/120/208/220/308/320`。bus 108在候选冻结前已有结果，因此明确标记为`legacy_seen_anchor`。六点normal prescreen只用于机械形成共同安全集，完整比较统一使用`A11/A12-1/A34/B12-1/B22/B6/C12-1/C27/C6/CA-1`和`121_NUCLEAR_1/213_CC_3/313_CC_1`，共同安全合同SHA-256为`7865c7544817acd2d0dd6a461766862af52f7175eb24f2c1466f52e70115aa87`。

四个可行候选的DC证书LB/UB依次为bus 120 `1207456.214789805/1207456.214789805 USD`、bus 320 `1207594.61558767/1207595.022772649 USD`、bus 220 `1207773.41079156/1207773.41079156 USD`、bus 108 `1212140.771918603/1212140.772348714 USD`。只有bus 120的UB严格低于其余可行候选LB。bus 208和308分别在加入`branch_B12-1_immediate`与`branch_C12-1_immediate`后的自由边界连续commitment LP前缀不可行，只能称冻结模型不可行。已冻结aggregate中的`ac_review_status=pending...`是其发布时状态；当前进度由独立AC结果推进，不修改旧aggregate。

AC合同固定bus 120/108、24小时、每小时全部24态和unity/0.95 lagging，共2304个direct PF。amendment-004批次分组收敛数为`574/576`、`574/576`、`575/576`和`573/576`，合计2296；0个case满足电压、支路、有功、无功和non-slack PG全部验收条件。四组V/支路/P/Q违规数依次为`574/177/304/571`、`574/177/304/571`、`575/179/425/560`和`573/184/437/515`，类别重叠且只统计收敛case。总体最低/最高电压为`0.650823991/1.125853399 p.u.`，最大电压违约`0.299176009 p.u.`，最大支路loading `2.129203046`，最大P/Q违约`257.547151763 MW`/`287.741739801 Mvar`。96个normal case全部收敛并全部有V违规，其中93个有Q违规。

amendment-003的`2276/2304`结果及manifest `2b5b705d...`因同址Q-inert机组覆盖唯一Q-capable控制器源`VG`而作废为父诊断；amendment-004结果manifest为`ee4894bba4e65433ffed4b31e4d96c78035bd2413dd4fa6accb3eb9f16c0609a`。独立零数据中心normal对照已经完成：24/24收敛、0/24 secure，24个小时均有V/Q违规，11个另有支路违规、10个另有P违规。该控制使用重新优化的无数据中心commitment且只覆盖normal，不是与treatment固定commitment、全状态逐case匹配的因果对照；但现有结果不能把失败归因于数据中心增量或POI。

零注入恢复诊断也已经完成。冻结primary PYPOWER 560的`reference_provider`和`distributed_committable`分别取得11/24与22/24独立审计见证；统一565 step-control仍为22/24，h15/h21未恢复。独立CasADi 3.7.2/IPOPT以`source/midpoint/flat_target_midq`三种固定初值运行原官方边界，每组同样为22/24，h15/h21均返回`Infeasible_Problem_Detected`；这不是全局不可行证明。`RATE_A`放宽5%和现有Q控制器边界扩展`+/-5 Mvar`探针均失败；电压上下限对称放宽`0.01 p.u.`后24/24成功，但最高`VM=1.06000001 p.u.`越过官方统一`VMAX=1.05`，不能替代主边界。IPOPT canonical v2以零求解器调用移除v1重复的`solver_objective_mw2`列，科学结果不变，prereg/result manifest分别为`ffdf5d5df29101b463438cbf753e6b80b6babd31d74ea72df82c9648cf236ab3`和`75d40ffe53ded9747f916d57a3d00921d5087549afc8148cb2953f5924bf7332`。

AC-aware commitment v1在正式结果前被真实输入校验阻塞：其core把每小时随在线机组和reference/controller选择变化的`BUS_TYPE`误列为跨小时静态字段。v1只发布了preregistration（input contract `2892a459137998fe7825acafc2391d9367f9cbfb66dcaeb2dc5c06f0a49237e8`）；candidate调用虽启动但在发布frontier前终止，joint AC solver调用数为0。失效记录manifest为`7ac6a6a2ecc76304376654b36d6a0e83e5bd506e9f3ff537356fa13ad94ac3dd`。v2只允许移除该错误静态相等项，同时每小时强制合法`PQ/PV/REF`和恰好一个`REF`；修复后的真实24小时preflight覆盖73台committable、72台reserve provider并通过，其余预算、目标、边界和初值不变。v2最终没有发布结果，运行性终止记录如下；这不能改变科学门禁。

2026-07-19运行控制复核发现，外层工具超时没有真正终止两个父进程已消失、无独立日志的`python -`计算进程：PID 28812于v1首次candidate调用后启动，PID 31872于v2首次前台调用后启动。两者均尚未创建正式frontier或隐藏staging，candidate阶段按实现也不调用joint AC。为防止已失效v1结果晚发布及v2重复进程并发执行原子目录发布，两者在任何candidate artifact出现前终止；随后只保留正式v2 PID 21468。PID 21468从2026-07-18 23:07:49 +08运行至2026-07-19 12:06:34 +08的停止请求，约46725秒内持续占用约一个逻辑核，但两份日志仍为0字节，且没有正式frontier、隐藏staging、partial checkpoint或joint AC调用。该次运行按用户授权停止；这不是不可行证据，也不知道停止时位于12个MIP中的哪一个。v2的配置、8项实现源码和注册输入已逐字节快照，运行性终止artifact manifest为`e8bcef7466a1dfa44e4c0a444eb297fbf7160cf1f7596485c86a6fd9984b799b`，v2科学协议本身没有因本次停止被宣告错误。

正式候选proxy模型实测规模为215689个变量、350615条约束；独立6小时pilot仍有53923个变量、87545条约束。compute环境已安装并原生/Pyomo smoke-test Gurobi 13.0.2、CPLEX 22.2.0.1和Xpress 9.9.1，但当前自动许可证的软件容量分别只有2000变量且2000约束、1000变量且1000约束、行列合计5000，均不能承载本模型；HiGHS 1.15.1是当前唯一通过正式容量门的引擎。完整inventory manifest为`ad39836b9ef94bc520ea2939750f9c4513b9db051d8c97513b813f566d97c9bf`；该判断仅是当前软件许可证容量与接口结论，不是法律意见，也不排除未来取得完整academic license后重新做独立benchmark。

线程选择使用与正式预算网格不同的前6小时、`0.0075`预算pilot，不生成正式candidate或调用joint AC。全24个预注册状态的同一proxy MILP在1/4/8线程下各运行两次、每次原生时限120秒，选择规则只读取termination、实际gap、独立残差和wall time，不读取目标值。4线程两次均以zero gap通过，中位求解时间117.2911719秒；8线程两次通过，中位120.7216602秒；1线程第二次到时限仍有0.003796157实际gap，因而不具重复资格。solver benchmark result manifest为`4b05c7d7fcbd8f64ddb9eb61d4ee15c571a7905d8ebd453ac19d07cbf56c63d1`，机械选择为4线程。实时JSONL与每次HiGHS原生日志已写入`results/logs`并与结果快照哈希一致。

正式算法比较使用相同的6小时、24状态冻结输入，单体全状态MILP与exact selected-state constraint generation各重复两次，仍不生成candidate或调用joint AC。exact-CG两次均通过最终24状态固定共享变量LP和独立残差审计，总时间为`54.057 s`和`54.502 s`；单体两次均到时限，实际认证区间宽度为`0.003796157`，不满足预注册资格。由非目标值规则机械选择exact-CG，preparation/result manifest分别为`ae3c19536341c0767f43dcbddb7ccabd60c9607f0baae7ab152507e750cf763a`和`82f1f0cb72d574b2054f193f6354383c5629bd30796b42a919323ef326c0d7e1`。

V3正式协议据此冻结为HiGHS 1.15.1、4线程、exact-CG。proxy最大化与cost最小化分别从同一seed重启，每轮对全部inactive state求解固定共享变量screen；未在screen时限内解析的状态标为`unresolved_promoted`并加入下一master，绝不作为不可行证据。每阶段只有在最终24状态fixed-shared LP、整数/残差审计和实际界证书均通过后才可被接受。实际区间定义为`[LB,UB]`、`absolute_gap=UB-LB`及`incumbent-relative gap=(UB-LB)/max(abs(feasible_bound),1e-12)`；目标值为`1e-4`，预注册最大相对接受值为`1e-3`，proxy另要求绝对gap不超过`1e-3`。这是随实际可行界和对偶界更新的动态误差区间，不是看结果后调整阈值。正式资格只读取stage顶层的`target_attained/eligibility_status/maximum_acceptance`；嵌套certificate中按`max(abs(LB),abs(UB),1)`归一的辅助relative gap和target字段只作诊断。cost-normalized commitment还必须通过primary proxy regret双门：不超过`stage1_absolute_gap + 1e-7 + 1e-6`且不超过`0.0010011`。

V3 preregistration manifest为`01646721d15395668bf0079cb6fe218dc0625187d1fbf108c5db74e47ae33f88`，input contract为`af4a388d80c211611a8e1dad3861936decb7f3c3e2de3a422116c87c013d8aa0`。历史正式attempt `formal_20260719T061959Z`在每次`solver.solve`期间启用30秒durable JSONL心跳，每次HiGHS调用保存独立原生日志；5秒配置是MIP报告行最小间隔，不保证每5秒产生一行。六个预算候选完成后分别原子发布checkpoint并支持严格resume校验，冻结父基线没有checkpoint。截至2026-07-19 14:32 +08，该进程当时仍有心跳和CPU进展，父基线已载入，首个预算候选仍在第一轮proxy master；尚无预算候选checkpoint、可行incumbent、完整实际gap、final 24-state audit或frontier。该历史状态没有故障或不可行证据，但也没有可报告的正式候选结果；attempt现已停止且不得恢复。六个预算checkpoint及包含父基线的完整requested frontier原子发布并逐项校验前禁止joint AC。

当前配置的“最快”只限于已注册比较矩阵。首个正式proxy master在`2801.9 s`才由树搜索找到incumbent，随后约5秒闭合zero gap并通过最终24状态审计；冻结父baseline其实是成本帽内的已知可行点，proxy为`0.24328147100424327`，但当前Pyomo `highs`接口报告`warm_start_capable=false`且实现没有MIP start。缺失warm start只影响time-to-first-incumbent，不改变可行域、dual bound或最终证书，因此不构成终止V3的正确性理由。若后继采用`appsi_highs`或native highspy，必须先通过独立重复pilot验证start映射、接受日志、运行时间、最终界和原单位残差，再新建预注册；不得在V3中临时切换。

V4 checkpoint JSON shape的repair-001后继没有产生正式结果。attempt `formal_repair_20260719T165115Z`因initial-proxy warm-start scope的iteration ordinal实现错误而走cold-start：PID 4684已死亡，progress无warm-start submission，native log无MIP-start接受/拒绝行且最后`BestSol=-inf`，预算checkpoint、frontier和joint AC调用数均为0。该停止不是数学不可行或无解证据，旧lease/attempt不得resume。只修正scope predicate并保留完整列、`HighsStatus.kOk`和native acceptance=1/rejection=0门的adapter修复已通过独立审查。新的implementation-only preregistration位于`results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_warmstart_scope_repair_002`，manifest为`0fec4eb7eeae5aa83cdbce41bfffc04c2f73b76a3ce64579b2b00e046417e4df`，input contract为`b9d40f95a0f5f24b546f77a6d21ee6f59c43e8d5e2732a64075fa82c8100cc21`；相对repair-001只允许runner和warm-start adapter两个实现SHA变化。冻结config `b107aba3908b04bbd677994ac272eeb98d35d5d957978dd42a70f5e44672b84b`、模型、预算、solver/算法/threads/seed、时限、gap/acceptance及joint AC协议不变。新attempt仍受第二amendment独立审查门禁，尚未启动。
repair-005 attempt `formal_repair_005_20260722T135158Z`完成四个prefix checkpoint后在candidate 5 `cost_normalization`留下最后heartbeat；PID 3744已停止，且无任何progress terminal event、candidate frontier或joint AC调用。该状态仅是`operational_interruption`，不构成正式失败、solver failure或不可行证据；active lease必须保留，旧attempt不得resume。operational interruption artifact manifest为`66fd455aa958c06c809f9a51a5a9588a932843b83b2cd2953b9982bd1bdb057b`；机器记录由`experiments/record_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_005_interruption.py`生成，当前门禁仍为false。

因此当前门禁固定为`treatment_followup_gate_passed=false`、`ac_security=false`、`security_certified=false`、`full_m6_model_input_ready=false`和`formal_vma_published=false`。当前无solver进程；`repair_005`旧attempt与stale lease不得resume，后续必须使用新attempt ID和新output root重新取得lease。该后继attempt只有在六个预算checkpoint、包含冻结父baseline的完整frontier、manifests、两阶段certificates、primary regret和final 24-state audit全部发布并验证后，才允许按冻结协议运行joint AC。所有历史V3/V4中断或失败attempt均不得恢复，也不构成数学不可行或无解证据；另一条解除路径是取得有来源的tap、可切换shunt、补偿设备及控制参数后分层启用。即使benchmark恢复成功，缺少真实接入拓扑、设备MVA、数据中心P/Q包络、converter Q和控制时序时仍不能签发工程安全结论。

首批公开生产数据已于2026-07-16取得并完成分源处理。Google PowerData 2019的55个可连接PDU经`bad_measurement_data`过滤后形成744小时形状；40,896个domain-hour完整，每小时有54或55个域，跨域只作无容量权重均值/中位数而不求和或插补。全窗峰值归一化只允许固定回放，不能跨train/holdout使用。Alibaba `stage1_core`全表审计覆盖1,055,501个job、1,261,050个task、1,055,032个group-tag和1,897台machine；主正GPU请求队列为732,318个task/714,903个job，缺失`plan_gpu`的223,965行保留为空且不填零。新增job-level包络保存release/completion代理、GPU请求和GPU-seconds，但不推断deadline或可恢复性。官方sensor表的3,033,232条实例生命周期平均记录已另行处理，形成576,724个完成候选job×GPU汇总；5,829个CPU usage、1,217个average memory及各3个网络字段缺失均单独计数，未填零。

NLR GenAI Power Profiles v2已按DOI `10.7799/3025227`、CC BY 4.0和归档SHA-256 `dcad6de800fb565d850b163902e2eddae48aabd1ed1c7336f9a1cdaf3012f137`冻结。2,467条实测profile来自4×NVIDIA H100节点，输出11个工作负载/规模组的source-defined CPU+GPU node-power统计；8条DIPLOEE whole-facility profile保持为独立合成证据。200条online-rate profile被上游插值到`0.001 s`，不作为1 kHz独立测量或高频ramp证据。NLR与PAI不共享job、硬件或时钟，因此该来源不解除正式映射门。

WattGPU固定Apache-2.0 commit `4e010359c167ac8c65b55aabd1aafbf765ae5d91`的8个对象已下载并逐哈希验证。4,798条LLM inference实验覆盖49个模型和8种实测GPU；T4提供精确型号硬件参考，V100/V100M32只作非精确架构参考，P100/MISC无覆盖。源数据200行prompt/generation请求数不一致，266行报告mean与`energy/duration`偏差超过1%，均由机器产物显式记录。统一门禁`rq2_data_readiness_v2`验证六个输入包、五份原始manifest及各包live config/implementation/module provenance；正式逐job映射门仍关闭。CFE/readiness v1仅保留为冻结predecessor，修订见`rq2_data_provenance_amendment_v2.md`。

Google受限配对查询已在项目`exalted-summer-490612-m6`完成。三次成功Job processed合计551,002,439,062 bytes、billed合计551,004,667,904 bytes，低于1 TiB门限；两个失败Job均未报告processed/billed字节。质量审计折叠1109个完全重复组，并对98个CPU冲突键保留上下界；233,888个多priority组进入`ambiguous`，963,596个无先验priority组使用显式`synthesized`标记。PowerData以`time-600000000`对齐，day-0的288个`production_power_util`样本全部质量不合格，因此只使用`measured_power_util`。

本地处理得到24行同系统小时配对和168行priority明细；CPU-time总下/上界为65,620,667.38184452/65,620,667.50039005 NCU-s，低优先级候选份额的小时边界范围为0.2860至0.4288。机器事件按ADD/REMOVE/UPDATE左闭状态重建，后续UPDATE不向前填补；`hour_index=18/19`共保留44.908767 unknown-capacity machine-seconds。该人口仍按`alloc_collection_id IS NULL OR 0`抽取且`population_is_complete_pdu_workload=false`，绝对PDU容量仍隐藏，priority候选不等于可削减或可恢复业务。Google、Alibaba和NLR没有可对齐的共同job与真实日历；不得拼成观测配对数据。ENTSO-E观测事故仍需令牌，RTS-GMLC故障率抽样只属`sampled_from_published_rate`；所以完整M6阻塞和全部正式认证字段保持不变。

在此基础上，day-0 builder把`measured_power_util_mean`直接乘以假设的250 MW参考容量，不做day-0峰值再归一化，生成24小时、`172.770833333333-189.729166666667 MW`的零柔性`derived_benchmark`。priority/NCU候选只保存在审计表，所有M6柔性、可恢复量和恢复headroom均为0。该builder产物自身仍保持`absolute_power_mw_available=false`、`flexibility_observed=false`、`full_m6_model_input_ready=false`、`chronological_dispatch_request_built=false`、`chronological_grid_dispatch_coupled=false`和`security_certified=false`；只有上述独立6小时或24小时runner的具名结果可把request/coupled两项置为`true`，其余证据和认证字段不变。

美国重大停电补充数据已按`us_major_power_outages_candidate_cohorts_v1`处理：1534源行保留不删，规范化候选键得到1521组，10个重复候选组涉及23行。主持续队列要求完整非负时间和报告时长大于0，共1385组/1398源行；另冻结已知失负荷751组、正失负荷611组、含零时长1463组等敏感性队列。重复组的失负荷/用户数保留非缺失max/min且绝不求和，reported/timestamp时长及31条`+/-60 min`差值均保留。预注册只固定描述性队列，不证明候选组是独立事故；该数据仍无branch/generator ID、拓扑、SCUC/SCED或同钟业务负荷，不能生成RTS具名事故或事故频率。

## F/X集合值规范

B0-B2不得通过任意小权重、未经校准的firm/X价差或假定事故频率选择唯一拆分。统一规则为：

1. 系统原有负荷、firm服务、关键N-1、工程工期和容量上限均为硬约束。
2. 主目标只最小化物理接入缺口能量；先保存主最优值及预注册数值容差。
3. 在同一主最优面上，分别最小化和最大化 `sum(hours[k] * X[k])`，得到可识别的X暴露区间。
4. 论文和结果表同时报告两个端点。需要一条展示轨迹时使用最小X端点，并标记为`conservative_minimum_x_normalization_not_economic_optimum`。
5. 合成投资和运行目标只能作为单独敏感性或更低层平局规则，不得把它们解释为真实社会福利。

若最小和最大端点不同，差异本身就是不可识别范围，不得隐藏。后续若取得firm/X真实价值差、容量持有成本和事故概率，可另做有单位、有基准年的经济场景，但不能覆盖集合值主结果。

## 成本求解边界

M3没有整数规划变量，原始凸二次目标现通过稀疏`standard_repn`直接交给OSQP。冻结完整模型的一次独占复跑得到：2075次迭代、QP求解约8.5秒、主残差`3.64e-8`、对偶残差`4.85e-10`、边界投影后原约束最大违约`5.97e-8`，低于项目`1e-6`门槛。HiGHS随后在完整线性可行域上执行L1线性可行性投影，目标改变`0.0512`合成单位，约为总目标的`1.0e-10`；最后的minimum-call LP为optimal。变量移动与目标偏差包络只用于数值可行性验收，不是最优间隙或误差证书。结果保存上述诊断，但因没有可行对偶下界和显式最优间隙，不使用“数学精确全局最优”表述。

M2当前只有“不启动”或在某一季度启动同一个捆绑工程这组有限离散选择。实现完整枚举这 $K+1$ 个固定启动候选，各候选把原始凸二次目标直接交给OSQP，审计原约束后由HiGHS修复剩余线性可行域；任一候选未解析时总体状态为枚举不完整，不输出正式最优选择。因此有限M2已不再依赖PWL近似或MIQP求解器。冻结RTS-24复跑在约113秒内解析全部5项并选择q1启动：目标`501360875.14`合成单位，距下一候选`74933666.62`，大于两侧数值修复包络之和；最大修复后原约束违约`8.11e-7`，428个状态-季度最大平衡残差`6.27e-8`。最大候选修复包络`11.04`只用于数值验收，不是最优间隙或误差证书。结果仍使用`synthetic_units`；因没有显式最优间隙证书，只能称完整候选枚举中的最佳已解析数值QP结果。未来扩展到多个可组合工程时，当前枚举不具备可扩展性，必须另行配置可复现的MIQP求解器或经测试的可扩展离散方法。

## 连续包络与T口径

连续包络使用一个不重置状态的时间序列，逐步记录调用、恢复和债务。当前显式压力轨迹以RTS-GMLC 2020的8784个连续时间戳作为日历，只把Area 1数值保留为未使用的审计列；它不把系统负荷代理当成数据中心业务负荷。

当前固定合同层在q3/q4均以250 MW满合同容量作为基线，恢复余量为0。只要发生一次需要恢复的正X调用，债务就不能在季度末归零。因此原静态结果`T100=q3`已不再成立；连续机制敏感性中可验证容量为`50/50/175/175 MW`，`T20=q1`、`T50=q3`，`T100`在q4右删失。该结果是对当前平坦基线的结构性反例，不是事故频率或特定企业合同证据。

正式逐时T需要同时具备：有来源的数据中心小时工作负荷和柔性比例、可恢复业务吞吐/恢复余量、事故起止和频次、逐时机组组合与爬坡、连续网络安全校核。缺一项都只能保留机制敏感性口径。

## repair-009 求解器切换与实现修订（2026-08-05 登记）

本节登记 repair-009 相对上文「HiGHS 1.15.1 是当前唯一通过正式容量门的引擎」（第119行）和「V3正式协议据此冻结为HiGHS 1.15.1、4线程、exact-CG」（第125行）的偏离。上文两处在冻结时是准确的，按 amendment 惯例保留原文，不改写。

### 已独立复核的事实

- repair-009 配置使用 `solver_name: gurobi`、`solver_threads: 4`（`configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml:66-67`）。
- 配置记录 `gurobi_pilot_benchmark_sha256sums: 63f7398eed5ef95e0de13b38ffb6efc7d08f4531c5df95da4f2fc6ce2af0da8d`（同文件第68行）。该值与磁盘上 `results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_gurobi_benchmark_v1/benchmark/SHA256SUMS` 的实测哈希一致，已独立复算。
- 引擎版本为 Gurobi 13.0.2：候选6的原生日志首行为 `Gurobi 13.0.2 (win64) logging started`、`Gurobi Optimizer version 13.0.2 build v13.0.2rc1 (win64)`；环境内 `gurobipy` 版本亦为 13.0.2。
- 候选6 level_set 原生日志显示 `Thread count: 8 physical cores, 16 logical processors, using up to 4 threads`，与配置的 4 线程一致。

### 尚未复核的事实

pilot 的具体运行结果（各线程档位的 wall time、gap、残差）本次未逐项读取 `benchmark/summary.json`，只核对了目录 manifest 哈希。学术许可的取得时点与许可类型亦未在本次核实。引用这些内容前需另行复核。

### 实现方式：runner 加载期 monkeypatch

`experiments/pilot_rts_gmlc_zero_dc_ac_aware_formulations.py`（冻结 HiGHS pilot）与 `src/grid/rts_gmlc_formal_cg_adapter.py` 均被哈希链锁定，不能改。切换改为在 runner-009 加载期打两处 monkeypatch，磁盘上被锁文件的哈希不变：

1. **`_frozen_pilot._solve_handle = _gurobi_solve_handle`**（runner-009:61）。覆盖 iteration≥2 的 proxy master、screening、full-state audit、level_set 与 cost bisection。
2. **`FormalCgModelAdapter.solve_master` 包装**（runner-009:65-130）。`rts_gmlc_formal_cg_adapter.py:239-245` 判定 `globally_infeasible` 时硬编码 `solver_api == "pyomo.contrib.solver.highs_v2"` 与 `termination_condition == provenInfeasible`。Gurobi 在 level_set 决策 MIP 下实报 `pyomo.environ.SolverFactory.gurobi_legacy` + `termination_condition=minFunctionValue` + `solver_status=aborted`，该条件永不成立，`globally_infeasible` 恒为 False，level-set 二分法的不可行通道对 Gurobi 完全关闭：既无可行 incumbent 抬下界，也无不可行证书压上界，最终抛 `strict_cost_separation_not_proven`。包装补回该通道——stage 为 `level_set_budget_feasibility`、求解器为 Gurobi、无可用 incumbent、且 `raw_lower_bound` 有限并严格超过 `decision_budget_cap_usd` 时置 `globally_infeasible=True`，与 HiGHS 的 `provenInfeasible` 同等对待。**未额外增加数值裕度门槛**：增加即等于对 Gurobi 施加比 HiGHS 基线更严的科学标准。`timeLimit` 终止被明确排除，符合 `timeout_or_ambiguous_is_infeasibility_evidence: false`。超出裕度写入 `decision_mip` 记录供审计。

同一 runner 另修一处与求解器无关的潜伏缺陷：`_validate_round_artifacts` 的链式传参。repair-005 起每层校验器进入时解包 `evidence["proxy_evidence"]`，但向父层只传该子映射，导致下一层 `KeyError('proxy_evidence')`。repair-005~008 均在候选5保存路径之前失败或中断，该路径从未执行，缺陷因此潜伏；repair-009 是首个真正走到候选5 checkpoint 保存的版本并触发它。修法为按中间祖先层数（repair-007→006→005）嵌套包装真实 proxy evidence，repair-004 作为叶子直接消费；`cost_evidence` 每层随行，各祖先重跑同一幂等成本检查。

runner-009 因上述改动的 SHA-256 变为 `c3c3c0c7b228bcaefc722b0b3ea55ea03365e241b737cfe40ad63929f5ce965c`，已同步写入配置 `implementation.runner_sha256` 并重新发布预注册。

### 验证状态

- **`proxy_evidence` 传参修订：真实链路已验证。** 候选5 checkpoint 成功原子发布，`checkpoint_manifest_sha256=a1bacf3706d7239aebdd1018c593675a2ea3e29c301a330e4bf64bb6d9d22aa9`，`reactive_proxy_fraction=0.29915134370579916`，`operating_cost_usd=1128585.043543376`。
- **Gurobi 不可行通道修订：仅有合成单测背书。** 8 个用例通过，含候选6实测数值（`Cutoff=1163877.341735611`、根界 `1163877.341851999`、超出 `1.16e-4 USD`）与 7 个必须不触发的负例（界未超上限、HiGHS 路径、错误 stage、有可行 incumbent、`timeLimit` 终止、界非有限、上限为 None）。**真实链路验证点是候选6，尚未取得。**

### 该路径并非全程 Gurobi

`src/grid/rts_gmlc_v4_initial_proxy_warmstart.py:81` 的 `V4InitialProxyWarmStartAdapter.solve_master` 在 `stage=proxy_maximization && kind=master && iteration==1` 时走自己的 Appsi/HiGHS warm-start 分支（`:106` `SolverFactory(warm_start["solver_interface"])`、`:114` `highs_runtime_options(...)`），完全绕过 `pilot._solve_handle`，因此 monkeypatch 对它无效。该调用仍是单核 HiGHS：候选5 实测 1.71 h、候选6 跑满 7200 s 上限，原生日志显示 `Using 1 max workers. Parallel search off`。该文件被 repair-004 的 `warm_start_adapter_sha256: c655a3d60af60655a4430000f87651441b888e7b949d8b853e86af45628efcd3` 锁定，未改动；曾尝试直接修改，`_verify_frozen_inputs` 立即抛 `repair-004 warm_start_adapter_path hash drifted`。

### 未闭合的程序性缺口

上文第129行要求换求解器「必须先通过独立重复pilot验证start映射、接受日志、运行时间、最终界和原单位残差，再新建预注册；不得在V3中临时切换」。本次两处 monkeypatch 属于实现变更，其效果尚未经过独立重复 pilot 复核。解除条件：对 monkeypatch 后的链路做独立重复 pilot，收集上述五项证据，据此建立新预注册。

## OPEN：候选6整数违约与求解器参数未生效（2026-08-08 登记，参数选择待定）

### 阻塞本体：IntFeasTol 与快照闸门差两个数量级

repair-009 候选6 在 `level_set_budget_feasibility` 第3轮返回 `maximum_integrality_violation = 5.030864294042203e-07`，`src/grid/rts_gmlc_formal_cg_adapter.py:217-220` 判 `usable=False`，快照被拒，前沿无法发布6个候选，下游 joint AC 被连带阻塞。

该数值不是求解器缺陷，是配置矛盾：

| 项 | 值 | 来源 |
|---|---|---|
| Gurobi `IntFeasTol` | `1e-6` | `gurobi_runtime_options` 用 `solver.feasibility_tolerance` 赋值 |
| 快照闸门 | `1e-8` | `candidate_snapshot.maximum_distance_to_nearest_binary_before_normalization` |
| 实测违约 | `5.03e-07` | 落在 `1e-6` 以内，求解器完全按配置执行 |

原生日志实证（`formal_repair_009_20260807T132046Z/06_q_proxy_delta_0p0500/level_set_round_03/level_set_budget_feasibility/level_set_budget_feasibility__iteration_01__master.log`）的 `Non-default parameters` 区段为 `Cutoff / TimeLimit 3600 / IntFeasTol 1e-06 / MIPGapAbs 0 / LogToConsole 0 / Threads 4`，无 `IntegralityFocus`。

HiGHS 时代该闸门从未被触发，属于 HiGHS 恰好返回更干净整数的偶然，不是设计保证。

### 已失效的 ifocus 尝试：预注册了无读取方的参数

`rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus`（attempt `candidate_20260808T135608923269Z_pid31300`）预注册 `formal_successor.solver_options.IntegralityFocus = 1`，跑满 5 h 59 m 后由用户决定终止，未到判决点。终止不是不可行证据。

失效原因是参数在两层被静默丢弃，两层都已独立复核：

1. `experiments/pilot_rts_gmlc_zero_dc_ac_aware_formulations_gurobi.py` 的 `gurobi_runtime_options` 只接具名参数，无 `**extra`；`_solve_handle` 亦只从 `solver_config` 的具名键构造 options，从不读 `solver_config["options"]`。
2. `src/grid/rts_gmlc_formal_cg_adapter.py:139-170` 的 `_call_config` 逐键重建 solver 字典，未枚举的键一律丢弃，因此即使 `_solve_handle` 读了也拿不到。

作废记录见 `results/tables/.../repair_009_ifocus/invalidation/invalidation.json`（schema `rts_gmlc_v4_repair_009_ifocus_unread_solver_option_invalidation_v1`），租约归档为 `7d2ec1a65d58404f98f3d58530b9341d.failed`。前缀候选1-4 检查点字节数与旧 output root 逐一相同，证明前缀导入确定性；这些检查点不作为有效产物计入。

### 已完成的通道修复（2026-08-08）

- `gurobi_runtime_options` 增加 `extra_options`；`FROZEN_GUROBI_OPTION_KEYS`（`MIPGap/MIPGapAbs/Seed/Threads/FeasibilityTol/OptimalityTol/TimeLimit/LogToConsole/LogFile/DisplayInterval/Cutoff`）拒绝被配置覆盖，避免配置悄悄改写冻结 pilot 选型；`IntFeasTol` 刻意不在冻结集内，是唯一可调容差。
- 新增 `assemble_gurobi_options`，含后置条件：声明的键若未出现在最终 options 中即抛 `UnreadableSolverOptionError`。`_solve_handle` 的 HiGHS 分支遇到非空 options 同样抛错，杜绝静默忽略。
- runner 新增第三处 monkeypatch，包装 `FormalCgModelAdapter._call_config` 把 `options` 挂回去（该文件被 repair-003/004 的 `formal_adapter_sha256: c66e7fc7e530baa0246a0ce70da75fb9fd475a2487b59b4758ffd077c6232788` 锁定，不能直接改）。
- runner 新增 `_verify_solver_options_are_readable`，在 `_verify_frozen_inputs` 内用真实装配函数对声明值做亚秒级探针，参数不可达则在预热前终止。
- `solve_started` 事件新增 `effective_solver_options` 与 `solver_api`，此后每次求解都在 `progress.jsonl` 留下实际下发参数的可审计记录。
- 新增 `tests/test_rts_gmlc_v4_repair_009_gurobi_solver_options.py`（12 用例）。相关回归 131 用例全通过。
- 端到端实证：Gurobi 13.0.2 原生日志 `Non-default parameters` 区段确认 `IntegralityFocus 1` 与 `IntFeasTol 1e-09` 均被应用。

**该修复只恢复了通道，未选定参数。** 通道修复本身不改变任何科学阈值。

### 已完成：持久化 cost audit 的 actual_proxy 容差对齐（2026-08-09）

ifocus2 attempt（`candidate_20260809T005341489745Z_pid32644`）在候选6的 `level_set` / cost 阶段整数违约为 0.0（`IntegralityFocus: 1` 对该目标生效），但落盘时失败于 `repair-005 persisted cost audit drifted`。

根因：`_validate_persisted_cost_audit` 用 `proxy_floor_absolute_tolerance = 1e-7` 比较连续重解的 `actual_proxy_fraction` 与候选 proxy；而 `FormalCgModelAdapter.audit_full_state` 接受同一审计时用的是 `feasibility_tolerance = 1e-6`。候选6实测差值 `1.0000000000287557e-7`，严格 `>` 越界；候选5同类差值 `9.999e-8` 侥幸通过。求解路径已 `passed=True`，失败仅在持久化门。

修复（仅 repair-009 runner）：`actual_proxy` 比较改用 `formal_solver.solver.feasibility_tolerance`；commitment 与候选 proxy 的恒等比较仍用 `proxy_floor_absolute_tolerance`。回归见 `tests/test_rts_gmlc_v4_repair_009_persisted_cost_audit.py`（复现候选6数值）。

该修复改变 `implementation.runner_sha256`，ifocus2 预注册不可原地续跑；后继需新 output root / 新预注册。候选1–5 检查点仍在 ifocus2 root，可作前缀导入源。

### 已完成：持久化 cost audit 的 snapshot.reactive_proxy 容差对齐（2026-08-10）

ifocus3 attempt（`candidate_20260809T230221675557Z_pid52492`）再次在候选6落盘失败于同一错误串 `repair-005 persisted cost audit drifted`。求解路径仍成功：`IntegralityFocus: 1`，`maximum_integrality_violation=0.0`，`cost_normalization` `eligibility_status=target_attained`；候选1–5 检查点已落盘。

根因：上一轮只放宽了 `actual_proxy_fraction` 比较，但 accepted cost snapshot 的 `reactive_proxy` 存的是同一连续重解值，与候选 commitment-capability proxy 的比较仍用 `proxy_floor_absolute_tolerance=1e-7`。候选5：`|snap-cand|≈9.999e-8` 侥幸过；候选6：`1.0000000000287557e-7` 严格 `>` 越界。

修复（仅 repair-009 runner）：`snapshot.reactive_proxy` vs 候选 proxy 同样改用 `feasibility_tolerance`；commitment-capability 恒等门不变。回归补 `test_cand6_snapshot_actual_proxy_gap_*`。ifocus3 不可原地续跑；后继 output root：`..._repair_009_ifocus4`。

### 已完成：ifocus4 候选前沿发布（2026-08-10/11）

ifocus4 attempt（`candidate_20260810T124707278538Z_pid13556`）在新 output root `..._repair_009_ifocus4` 上完成 prepare + generate-candidates：候选1–6检查点全部落盘，`candidate_frontier` 已发布（`summary.json` schema `rts_gmlc_v4_repair_009_candidate_frontier_v1`，`unique_candidate_count=7`，含 parent baseline）。`IntegralityFocus: 1` 仍在求解器选项中；候选6不再被持久化 cost-audit 门拒绝。`joint_ac_solver_call_count` 仍为 0；该前沿仍是 derived benchmark / 非工程安全证书。

### 进行中：ifocus4 `run-joint-ac`（2026-08-11 启动，preflight 失败后补全修正案）

首次尝试在入口校验失败：`repair-005 frontier summary drifted`（未进入 IPOPT；`joint_ac` 未发布）。

根因（两层）：
1. generate 在进程内把 `formal_solver.solver` 改成 Gurobi 后才发布 `summary.json`；fresh `_build_context` 仍用 HiGHS → summary 重建不一致。
2. 仅修 (1) 并更新 `implementation.runner_sha256` 后，会打破 ifocus4 冻结链：前沿/检查点仍绑定旧 `input_contract_sha256`，而 live prereg 期望新 contract。

修复（仅 repair-009 runner）：
- `_apply_formal_successor_solver_override` 在 `_build_context` 全局应用 Gurobi 合约；
- `_load_candidate_frontier` 以已发布 `summary.input_contract_sha256` 作为检查点 reload 权威；
- 新增 `amend-preregistration-implementation` stage：只允许 implementation hash / `successor_config_sha256` 变更，归档旧 prereg，保留 frontier；嵌套归档改用 `_write_nested_manifest`（避免漏记 `previous_preregistration/SHA256SUMS`）；
- ifocus4 预注册已纠正发布（live contract `ea992b98…`；frontier 仍绑定生成时 `0b34bfe9…`）。

第二次 `run-joint-ac` 仍在 preflight 失败：`repair-004 level-set round chain drifted`（约 4.5h `_build_context` 后；未进入 IPOPT；`joint_ac` 未发布）。根因：检查点 round JSON 冻结生成时 contract `0b34bfe9…`，而 leaf 校验对比 live amended contract。修复：`_validate_round_artifacts` / `_load_candidate_checkpoint` 在传入已发布 frontier contract 时，用其桥接 round 校验；再做一次 implementation-only prereg 修订后重跑 `run-joint-ac`。

### 已终止：ifocus4 首次 joint-AC 子进程是 honest incomplete（2026-08-12）

attempt `joint_20260812T044759183290Z_pid13700`（父 PID `13700`，worker PID `21172`）在首次 `candidate_00/source` 上于 parent 计时 `7500.494260399952 s` 超时。权威证据为：

- progress：`results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus4/joint_20260812T044759183290Z_pid13700/progress.jsonl`，声明 `expected_joint_call_count=21`，终止时 `completed_joint_call_count=0`；
- call registry：`results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus4/joint_call_registry/candidate_00__source/call.json`，manifest SHA-256 `0a56007ff240ccdfcad7ff1cea51b55dd96276112fded0f415744277a228d4f1`；
- execution lease：`results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus4/execution_lease/history/668f668226db419484387c8b6419669e.failed/{lease.json,terminal.json}`；
- worker process log `.../worker_process/candidate_00__source.log` 为 `0 bytes`；不存在 `.../native/candidate_00__source.log`，也没有 worker result/checkpoint 或 `joint_ac` 发布目录。

该旧协议从子进程创建时即启动 `7500 s` wall deadline，没有 worker 内阶段事件，因而证据只能支持“在验证 IPOPT solver start 之前或其可观测性之前超时”的 **honest incomplete**。它不能定位为模型构造的某个具体函数卡点，不能解释为 IPOPT/模型不可行，也不计为已完成 solver call。最终计数固定为 `0/21`；旧 attempt、call registration 和 lease 不得 resume/retry 或原地改写。

repair-010 后继 orchestration 已接入既有 immutable call registration、worker result、checkpoint 与 execution lease：fresh isolated worker 持久记录 `worker_started → context_load_started/completed → prepared_cases_completed → nlp_build_started/completed → solver_started → solver_finished` 的 hash-bound、flush+fsync phase journal；父进程以实际 spawn PID、aware timestamp、单调 worker elapsed、重算后的 expression/solver-input fingerprints 和冻结的 prepared/IPOPT/software identity 验证记录，只有完整验证 `solver_started` 后才开始 `7500 s` solver wall，IPOPT CPU `7200 s` 不变，并负责 terminate/kill/grace、worker exit和result manifest验证。startup limit 尚无 fresh-worker校准证据，保持 `null`；`formal_execution_ready=false`且successor preregistration未发布，因此prepare/formal-run/worker CLI在spawn前fail closed。lightweight context artifact 的完整语义等价性未证明，保持`disabled_unproven`，但这只禁用artifact路径；`fresh_rebuild_in_fresh_isolated_worker` fallback已冻结且不由artifact gate阻塞。不得把主进程 fresh `_build_context` 的约 `4.5–5.2 h` 直接当成 child startup limit。

repair-010 的 recovery 接受门不再继承旧 repair-004/009 attempt：existing worker result、existing checkpoint、最终 `joint_ac` load/merge 都必须有 repair-010-local phase registration、父进程实际 PID spawn receipt、completion receipt、完整 journal、call/input/frontier/candidate/commitment/dispatch/IPOPT/software/fingerprint 和 result/native manifest 的一致绑定；缺失或 drift 均停止且不得补造、重试或解释为 solver/不可行证据。completion receipt 发布或后置重验证失败时，已验证的 `solver_started` 固定分类为一项 honest-incomplete call；recovery completion 缺失/损坏时仅在 registration + spawn receipt + journal 完整验证到 `solver_started` 后计 1，pre-solver 或坏 journal 计 0，worker result 本身不用于推断。旧 ifocus4 frontier 也不能由 solver 直接跨 root 读取，只能经显式 `import-predecessor-frontier` 使用 repair-009 权威 loader 审计全部 preregistration/frontier、7 candidates、6 checkpoints 和 22 nested round manifests 后原子深复制到 successor-local import；import record 固定 source outcomes 已观察、scientific values unchanged、solver calls `0`、无 hard link。当前未发布 prereg、startup limit 为 `null`，所以 import/run 同样在写 root 或 spawn 前 fail closed；真实 ifocus4 本轮仅只读审计，不创建 repair-010 root。

repair-010 进一步冻结 parent finalization 状态机：可信 solver completion 后先原子发布 hash-bound intent；其后任一 completion/revalidation/checkpoint 或 success-seal commit 前 failure 均必须发布不可变 terminal-incomplete tombstone，固定计 1 次 call、非 infeasibility、禁止 resume。success seal 只能在 completion、checkpoint 与 parent完成事件后最后发布并绑定三者 manifest；若底层 publisher 在 atomic rename 后抛错，只有 target manifest 与预计算 exact payload 完整一致才按 committed success 继续，且不得调用 terminal publisher。target 已存在但无法证明 exact commit 时为 commit-indeterminate fail-closed 状态，不得同时登记 terminal incomplete。四类恢复入口按 terminal → intent/success seal → completion 的顺序 fail closed；terminal 损坏/绑定漂移拒绝接受。若 tombstone 自身发布失败，intent 存在而 success seal 缺失仍阻止既有 completion 被未来接受，同时抛显式 persistence error，不虚报 tombstone 已持久化。该机制不改变 pre-solver count 0 分类，也不解除 startup/prereg/formal readiness blocker。

repair-010 startup calibration V1 was started once and ended after about 30 seconds as an immutable honest calibration incomplete: parent PID `18576`, worker PID `31312`, journal contains only `worker_started → context_load_started`, reason `calibration_worker_exit_code:1`, solver calls `0`, no native IPOPT log, non-infeasibility, and no-resume. Its contract/registration/spawn/incomplete manifest SHA-256 values are `a4ed4af3816061c42420a031f16a694827278fe94cda4e52cb8a980972eefa5f`, `2a3c20658cea11fc5f0ccb4b0e23d87f0e634d3f53815f8dc58c23b73582ee54`, `c8b951e64ede31017845b8c7ccefdbaf21f4c607b4af9ffa8faf13c9006e4e68`, and `4f3ba6e497e388c2e9713355f7e7a035fb8387c6f60b07958b711c884244930d`. The inherited repair-009→004 loader rejected checkpoint input-contract drift because repair-010 instrumentation had changed the shared V4 adapter from historical SHA `cf5cf1e3d133b7e60f63dbb0d072952a9e78de24cd05d0bb740683e8806013b7`; this is a successor implementation-isolation defect, not environment failure, old checkpoint corruption, solver evidence, or infeasibility.

The calibration implementation now fixes the exact timing and terminal commit boundaries: start is sampled after log open immediately before `Popen`; stop is sampled only after full actual-PID/binding/journal/fingerprint validation, so validation time is included. Completion post-rename exceptions are reconciled against the exact precomputed payload/manifest; only a proven commit is success, an absent target may become incomplete, and an unprovable or completion+incomplete state is permanently rejected. The launcher publishes request intent before spawn and actual-PID/started receipts afterward; any post-spawn receipt failure terminates/kills and waits for only its child before publishing immutable failed state. Failure to prove child death plus failed receipt is unrecoverable and the launcher root still blocks retry. These mechanisms have only tiny/analytic fault-injection evidence and do not change the unresolved real startup-calibration blocker.

The isolation defect is repaired without weakening the loader: the shared V4 adapter is restored exactly to the historical authority SHA, and observer/fingerprint/pre-solver-stop behavior lives only in `rts_gmlc_ac_aware_commitment_v4_repair_010_adapter.py`. Both calibration and formal joint workers now call that dedicated module directly; the formal worker uses a repair-010-local executor that reuses the legacy row/validation/metadata/publication helpers and forwards the phase observer, rather than entering the legacy executor's runtime shared-adapter import. Calibration V2 has a new ID and disjoint table/log/launcher roots, binds both adapter hashes, verifies the four repair-004 checkpoint contracts plus V1 immutable evidence before launch, and preserves the frozen single-sample/`21600 s`/`ceil((2*elapsed)/300)*300` rule. V2 has not been run and cannot reuse V1. Therefore `startup_limit_seconds: null`, unpublished preregistration, and `formal_execution_ready=false` remain active blockers.

### 顺带修复：发布目录被 .pyc 污染会阻断下次启动

`results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_warmstart_benchmark_v3/preparation/__pycache__/benchmark.cpython-312.pyc` 由候选5 warm start 经 `_load_frozen_benchmark_module` 动态导入时写入（实测生成于 2026-08-08T13:56:20Z）。它使该目录文件集偏离 `SHA256SUMS`，`_verify_solver_predecessors` → `_verify_manifest` 在下一次启动即抛 `Source manifest file set drifted`。即每一次跑到候选5 的运行都会给下一次运行埋雷。已删除该字节码；后继 launcher 必须设 `PYTHONDONTWRITEBYTECODE=1`。

### 参数选择：待用户决定，两条路证据不对称

Gurobi 官方文档（Parameter Reference，`IntegralityFocus` 与 `IntFeasTol` 条目）对本失败模式的判断是：

- 本模型正是文档描述的 big-M trickle flow 结构（原生日志 `Matrix [4e-03, 6e+04]`、`RHS [1e-01, 1e+06]`，并有 `WARNING: Problem has some excessively large row bounds`）。
- 文档原文：「Reducing the value of the IntFeasTol parameter can mitigate the effects of such trickle flows, but often at a significant cost, and often with limited success. The IntegralityFocus parameter provides a better alternative.」
- Gurobi 支持文档另警告 `IntFeasTol = 1e-9` 配合宽松 FeasibilityTol 可能导致数值精度问题与错误变量固定，把可行模型报为不可行。

因此把 `IntFeasTol` 收到 `1e-9` 并非厂商推荐路径，且在本项目有特殊风险：出问题的正是 `level_set_budget_feasibility` 决策 MIP，它的用途就是证明「预算上限内无解」。一个由过紧容差诱发的伪不可行，与 agent.md「不得把局部不可行状态重新解释为数学不可行」直接冲突，且 repair-009 的 Gurobi cutoff 不可行通道补丁会把它当作真证书接受。

`IntegralityFocus: 1` 的代价是「modest performance penalty」，不引入伪不可行风险，但文档也明说「the solver won't always succeed」，即不保证 ≤1e-8。

三条路各自的性质：（a）仅 `IntegralityFocus: 1`，厂商推荐、无伪不可行风险、不保证成功；（b）仅 `IntFeasTol: 1e-9`，直接约束违约上界但有伪不可行风险且厂商称收效有限；（c）两者并用，成功率最高但保留（b）的风险且失败时无法归因。

**本节只登记证据，参数未写入 config。** `configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml:68-69` 仍为已证明无效的 `solver_options: {IntegralityFocus: 1}`，在选定并重新预注册之前不得据此启动正式运行。

## gap 阈值放宽与预注册规格冲突（repair-010 已选择路径 a，formal 仍阻塞）

`metrics_and_validation.md:411` 与 `formulation.md:344` 均写明 maximum accepted relative gap 在正式运行前冻结为 `1e-3`，且 `:411` 明确「不得按结果修改时限或阈值」。配置实测值：

| 版本 | `maximum_accepted_relative_gap_to_feasible_incumbent` |
|---|---|
| v3 / v4 / repair-003~006 | `1.0e-3` |
| repair-007 | `1.2e-3` |
| repair-008 / repair-009 | `1.5e-3` |

git 提交信息：`7297887 feat(repair-007): 放宽 maximum_accepted_relative_gap 至 0.12% 解除 candidate5 阻塞`；`c91b140 feat(repair-008): 阈值提至 0.15% 覆盖两个已观测的候选5证书`。后者与规格禁止「按结果修改阈值」直接冲突。

同时 repair-009 的 `registration.json` 记录 `candidate_frontier_outcomes_observed: false`，与「已观测候选5证书」不能同时为真。

本节只登记事实，不预判处置。两条可选路径：（a）退回 `1e-3`，按规格把候选5标记为 `eligible_within_maximum` 而非 target attained；（b）保留 `1.5e-3`，但在预注册中显式记录修订时点与理由，并把 `candidate_frontier_outcomes_observed` 改为 `true`。处置未定前，该 gap 阈值与候选5的资格状态不得写入论文正式结论。

### 处置意向：倾向路径（a），执行时点在候选6真实链路验证之后

以下数据取自 Gurobi 下候选5的已落盘检查点 `stage_audits`（备份路径 `.backup_repair009_output_20260805T113832Z/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009/candidate_checkpoints/05_q_proxy_delta_0p0200/candidate.json`，checkpoint manifest `a1bacf3706d7239aebdd1018c593675a2ea3e29c301a330e4bf64bb6d9d22aa9`）：

| 阶段 | incumbent-relative gap | `target_attained` | 相对冻结值 `1e-3` 的富余 |
|---|---|---|---|
| `proxy_maximization_hybrid` | `8.979707997056543e-05` | True | 11.1 倍 |
| `cost_normalization_hybrid` | `9.734785510674134e-05` | True | 10.3 倍 |

两个 gap 均已低于 `target_relative_gap = 1e-4`，不只是低于最大门 `1e-3`。即：**在 Gurobi 下候选5根本不需要那次放宽**，路径（a）不会使候选5降级为 `eligible_within_maximum`，它仍是 target attained。这与登记时的初步判断不同，登记时尚未核对检查点内的实际 gap。

放宽的动因是求解器缺陷而非科学需要。repair-007 config 记录的失败原因为 `heuristic_cost_gap_variance_across_proxy_paths_and_highs_time_limits`，即 HiGHS 在不同 proxy 路径下 cost gap 方差过大；Gurobi 下该 gap 收敛至 `1e-5` 量级。保留 `1.5e-3` 等于保留一个已失效缺陷的补丁。

同一检查点内还留有跨版本继承的阈值不一致：`proxy_evidence.certificate.maximum_accepted_relative_gap_to_feasible_incumbent = 0.0012`（repair-007 值），而 `proxy_evidence.direct_stage_record.maximum_acceptance.maximum_accepted_relative_gap_to_feasible_incumbent = 0.0015`（repair-008/009 值）。退回 `1e-3` 会一并消除该不一致。

不立即执行的理由：退回需改 config → runner 哈希链变 → 重新预注册（实测约 4.5 h）→ 候选5重跑（实测约 3 h），合计约 7.5 h。而该阈值对候选6无影响——候选6 proxy 阶段在 7200 s 上限处 gap 约 0.87%，超过 `1e-3`/`1.2e-3`/`1.5e-3` 全部三个值，无论取哪个都会进入 `level_set_budget_feasibility` 回退路径。若现在改而候选6随后暴露新缺陷，这 7.5 h 需重付一次。

因此执行顺序为：候选6 完成并验证 Gurobi 不可行通道补丁 → 确认无新缺陷 → 一次性执行阈值退回与最终全量重跑。退回后候选5的数值不变（两个 gap 在两个阈值下均通过），变化仅限契约中记录的阈值与标签。

**本节只记录意向，config 未改动**：`configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml:86` 仍为 `1.5e-3`。在执行退回并重新发布预注册之前，本节开头的处置未定约束继续生效。

### repair-010 处置

用户已明确授权路径（a）。旧 repair-009 config/preregistration/frontier 保持不可变 predecessor evidence；新 `configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_010.yaml` 将 `maximum_accepted_relative_gap_to_feasible_incumbent` 冻结回规格值 `1e-3`，并将 `candidate_frontier_outcomes_observed` 诚实登记为 `true`。这解决了 successor 设计中的 gap/observability 口径冲突，但不追溯改写 repair-009 产物。repair-010 当前因 startup limit 未校准、`formal_execution_ready=false`且successor preregistration未发布而 fail closed；context artifact等价性未证明只关闭artifact路径，不关闭fresh-rebuild fallback。阈值处置不得解释为 formal result 已完成。

## 外部证据阻塞

### RTS-24响应与频率

PYPOWER RTS-24的33台机组没有可用10/30分钟爬坡数据；源值为0，加载器按缺失处理。RTS-GMLC是独立73节点系统，机组集合和Pmin不一致，其ramp不能直接回填。

解除条件：逐台机组版本化映射、上下调MW/min或10/30分钟能力、响应起止时间、备用类型与headroom、适用开停机状态，以及`RATE_A/B/C`持续时间来源。若评价机组跳闸频率安全，还需惯量、RoCoF、频率最低点及一次/二次响应轨迹。

### branch 10孤岛

branch 10是7-8单一连接。`allow_islanding=True`只能证明每个分量的静态DC平衡，不能证明保护、频率、电压、再同步和恢复可接受。

解除条件三选一：可靠性标准允许排除该事故的依据；具有保护定值、UFLS/UVLS、动态校核和恢复流程的计划孤岛方案；或新增第二通道消除割边并把branch 10纳回正式事故集。

### 扩建AC参数

现有配置只有branch 11/12的`RATE_A/C +100 MW`和POI `+200 MW`。缺少RATE_B及持续时间、MVA额定、R/X/B、主变阻抗和tap、数据中心P/Q或功率因数包络、无功设备、母线电压设定与控制时序。

解除条件：提供设备清单和拓扑映射、上述电气与控制参数，并对正常态和完整N-1执行AC校核。M1候选补救不是已安装工程，不能转作证据。

### 逐时运行

RTS-GMLC原始73节点系统具有负荷、风、PV、RTPV、水电、机组ramp和最小开停机字段；原生路径已完成完整day-0 24小时selected-N-1 day-ahead DC SCUC/固定组合ED软件benchmark，包含启动、按小时上取整的最小开停机、跨时ramp和三区Spin备用，并完成两个代表POI的amendment-004无补救direct AC sensitivity、零数据中心normal对照以及560/565/IPOPT恢复诊断。其初值仍是优化派生自由边界而非观测历史，事故表和`completed_periods`为空；direct与zero control均为0 secure，官方电压边界内h15/h21仍无共同恢复见证，且没有工程接入参数，仍未覆盖实时SCED、full-N1或工程级AC安全。因此这里只解除具名软件benchmark的计算与诊断门。另一条RTS-24路径仍需建立可审计的33台机组聚合映射并补齐新能源母线、容量和UID映射，原生RTS-GMLC结果不能直接解除该映射阻塞。

## RQ2三区域相图退化（2026-08-24，阻塞TSG主张）

冻结的本地derived benchmark
`results/tables/rq2_three_region_phase_map_v1`已完成70/70 cells并通过计算门：

- `R1_no_conflict=0`；
- `R2_double_commitment_risk=0`；
- `R3_common_insufficiency=69`；
- `diagnostic_mixed=1`；
- `unresolved=0`。

其中50格correct/B6 training均由HiGHS证明不可行，19格在共享holdout上等价失败。唯一mixed格为Bus 8、`alpha_hr=0.50`、q99、20 MW业务恢复headroom：correct/B6分别提交12.00/14.02 MW，二者失败概率均为1，B6期望短缺反而低约1.01 MWh。该结果不支持“B6在数据驱动时序下稳健增加场景外风险”，也没有识别出三区域边界。结果与CFE scarcity或恢复约束压倒合同核算差异的解释一致，但50个training不可行cell尚未做逐约束归因，因此不能写成已识别的因果机制。

该结果不得通过查看结果后降低CFE目标、增加恢复headroom、改变窗口或筛选POI来修复。当前TSG主张保持阻塞。解除条件至少满足其一：

1. 获得外部合同/业务证据，独立冻结可辩护的恢复能力、deadline和CFE恢复核算参数，再注册新的外部验证；
2. 获得同钟网络事件、负荷和CFE联合时序，替代独立边缘配对；
3. 将论文问题重构为“严格小时CFE下的共同不足边界”，并补充与该新问题直接对应的理论或经验贡献。

现有70-cell结果、manifest和图表必须保留为完整阴性证据，不能删除或覆盖。其`security_certified=false`、`formal_result=false`、`empirical_probability_claimed=false`状态不得提升。

## RQ2公开边缘24小时successor门（2026-08-24）

公开数据后继的软件与输入配置已闭环，但正式数值证据尚未生成：

- Alibaba v3使用24小时块、training-only peak normalization和job-level
  双侧排除，得到34个training与34个holdout块；manifest SHA-256为
  `62f2ec5eefd0c651d8b970a16fce4fb6336ccb75ab09e3d2c67386cc26edb524`。
- RTS-GMLC v4使用93台enabled generator与118条non-islanding AC branch，
  system-level competing-risk chronology保证任一小时最多一个N-1停运，
  得到541个training与530个holdout 24小时块；manifest SHA-256为
  `28bc2c3c1ee3ba0ef6c940aec56f66d49587b5f2895d0e6b0b83fb0b6360cc63`。
- `rts_gmlc_public_grid_need_dispatch_v2`已通过1071-block provenance preflight；
  v1的单个真实24小时block smoke只保留为开发证据。v2正常态SCUC只冻结
  commitment/dispatch；事故小时
  corrective LP最小化POI削减。全削减仍不可行时返回
  `proven_infeasible=true, grid_need=None`，不伪造有限调用。
- pairwise successor只用training代表点冻结correct/B6 minimum-capacity
  full-service策略。CFE请求截断到逐时可用业务柔性，物理`grid_need`不截断；
  holdout在true shared envelope下固定策略执行。training策略不可行的cell
  单列为fixed-policy estimand未定义，不生成虚构pairwise指标。
- identification successor对每个eligible cell要求完整
  `530 × 34` Cartesian outcome，输出九个注册指标的sharp lower/upper bound、
  optimizing coupling、independent/comonotone/countermonotone诊断和无参数
  先验的OAT ambiguity-reduction区间。

v5 pipeline provenance contract除绑定实际runner、grid-need/SCUC或policy
模块与solver版本，并逐级复核上游config、implementation、source和package
身份外，还严格证明checkpoint inventory required key set完整。grid键集合
等于全部注册block IDs；pairwise键集合等于全部cell policy checkpoints与
eligible cells的完整Cartesian pair checkpoints；digest限定为小写hex
SHA-256。v4保留为失败的predecessor，不得用于正式运行。

v5独立R4已`PASS`，用户已授权，且grid-stage activation只把review/formal
两门从false改为true并绑定全部live hash。grid stage允许正式执行；pairwise与
identification仍在上游包发布和验证前保持关闭。当前仍不是
`formal_result_ready`，不得把preflight、partial checkpoint或未解析结果写成
正式结果；也不得把RTS抽样事故称为经验事故概率，或提升
`security_certified=false`。

### v6 E0与执行机successor（2026-08-25）

v5正式HiGHS grid attempt保留202/1071个checkpoint，未继续运行。v5
manifest锁定的旧`formulation.md`字节已不在当前worktree或可达Git历史，
因此这些checkpoint仅保留为非正式诊断证据，禁止formal resume，也不是v6
执行输入；旧`rts_gmlc_public_grid_need_dispatch_v3_formal.yaml`的三项执行门
已全部关闭。开发机对
`holdout_s20260822_0089`的source hour 6598和
`holdout_s20260822_0150`的8057--8059完成冻结小规模诊断：原corrective LP
不可行，`D_DC=0`端点仍不可行，放宽AC branch continuous ratings后4/4恢复
finite。该证据只支持冻结selected-N-1 DC benchmark内的网络热约束外生
不可行，不是业务柔性共同不足、总发电容量不足或工程安全结论。

v6新增`exogenous_grid_infeasibility`（E0）状态：不填有限`grid_need`，保留
无条件边缘质量与全部Cartesian状态行，contract-risk transport只条件于
finite-grid blocks，E0不进入R3。capacity estimand改为
`normalized minimum flexibility underprovisioning`；当前模型没有显式$X$
决策，禁止使用“$X$高估”表述。代表点策略须通过完整evaluable training
support；partial区域须由同一transport coupling见证；另报告固定seed
marginal block bootstrap endpoint intervals。

新Gurobi successor使用独立v4 config、checkpoint和output目录，并在
`GQPD263XH9`开发机上由hostname与环境变量双门fail closed。冻结四块
HiGHS/Gurobi v1 pilot现已在执行机完整运行并回传，但原预注册比较器得到
`268/280 PASS`、`eligible=false`；详细失败与semantic successor见下文2026-08-27小节。
因此`cross_solver_confirmation_completed=false`、`formal_execution_ready=false`继续成立。
开发机实现与handoff的独立R4 PASS不覆盖本次observed-result语义修订；在新确认性pilot与
基于其回传证据的新activation完成前，不得启动全量grid、pairwise或identification。
v1结果尚未观察时补齐的normal SCUC incumbent-relative gap字段保持原样；本次不改其schema、
模型、阈值、block或estimand。

#### Windows executor v2 successor（2026-08-25）

旧v6 preregistration、outer manifest、executor bundle、冻结测试和历史结果保持字节
不变。旧测试在Windows上有两处`str(Path)`与POSIX manifest key的分隔符假失败；v2
先绑定旧test SHA，仅对两个精确nodeid作`win32` strict xfail，并由新canonical-path
测试完整承接inventory/hash门，禁止全局Path monkeypatch或静默ignore。
新非循环权威链的outer SHA-256为
`32bde980733ef80b04571d1fe328c893ff78b4ecb1aee2150c318970707e4942`，其唯一inventory
成员v2 bundle SHA-256为
`10129f473a521f37ae0c45bf89a4904c77156c92dcc55837adf91adb8d58e37e`；runner先验outer，
再验bundle及bundle members。

`scripts/run_experiment.ps1`新增白名单`rq2-public-pilot`，唯一顺序为
`verify -> preflight -> pilot -> package-pilot`。它要求显式绝对普通文件
`RQ2_EXECUTOR_PYTHON_EXE`，不复用`compute`/PATH；独立
`RQ2_PILOT_TIMEOUT_SECONDS`缺省和最小值均为21600秒，timeout不作为不可行证据。
timeout后必须由Kill、有限grace WaitForExit、Refresh与HasExited共同证明child退出；不能
证明时固定failed并禁止成功工件验证。四阶段未完整成功只保留诊断日志；成功门要求四阶段
stdout/stderr共8个非reparse普通文件并逐项验证复制后SHA。
冻结executor在Windows生成的package receipt原生反斜杠会先经严格仓库相对路径
canonicalization；absolute、drive、UNC或traversal receipt均fail closed，再与注册的POSIX
路径作精确比较。
preflight、pilot、transfer package/manifest和逐阶段日志必须递归进入
`RUN_ARTIFACT_DIR`，缺件时即使子进程退出0也fail closed。该successor只修执行与
工件边界；该入口现已完成v1 pilot与transfer回传，但原comparison失败，仍不构成R4 activation
或formal result；当前仍为
`cross_solver_confirmation_completed=false`、`formal_execution_ready=false`。
旧H2 temporal preregistration v1同时冻结了共享executor旧SHA；其科学输入与旧manifest
保持不变，由versioned successor manifest/validator只替换executor入口binding，并完整
重放旧validator的17-job、threshold、seed、sample size与gate语义。旧test只有在精确证明
当前失败为executor SHA mismatch时才strict-xfail，其他失败直接关闭collection。该amendment
不改变模型/solver语义或既有结果，也不解除H2自身的`formal_execution_ready=false`。

另登记独立R3 residual：science单进程独立运行10项通过，而同一进程先运行formal-batch首测
后有3项unresolved，指向HiGHS全局thread scheduler状态污染，不是数学不可行证据。pilot
四阶段各自启动独立进程且threads冻结为4，但正式授权前仍需针对性诊断证明进程隔离充分；
本successor不修改solver/thread语义。

#### RQ2 executor环境可重建successor（2026-08-27）

在执行机上按冻结`environments/rq2_executor_v1.yml`创建的全新环境无法导入冻结executor：
首次缺失依赖为`pypower`，继续审计还确认eager import需要`osqp`。失败发生在solver call和
结果写入之前，因此只登记为执行环境依赖闭包阻塞，不登记为模型/数学不可行。

versioned `environments/rq2_executor_v2.yml`固定补入`pypower==5.1.19`和`osqp==1.0.5`；
其SHA256为`310b5c2f1261678269cf2e1424255f48582975aec7e492fe029f45cd5e73bdf6`。
环境successor validator/config/manifest SHA256分别为
`405373122cb2299d0930ac552d5ba0dfad08aab864902234bbd43447fe847abc`、
`22f93851a42882981f2f1183a1cb02251dd23e30576ffdd71c3865dbbeba61e5`和
`f5e1ad0c5e85cce64ae3e2b7e66ed9508546a9730d67de111fe1cff051cc76ec`。旧v1环境、handoff
v2、outer/bundle、冻结executor均保持字节不变；successor不改变solver、算法、线程、seed、
阈值、pilot block或科学口径。

解除本环境阻塞的最小证据是：从v2 YAML创建全新prefix；runtime validator精确核对Python与
全部直接依赖版本并真实import冻结入口；冻结executor `verify`通过；全过程在preflight前保持
0 solver call与0 result write。本机已从v2 YAML创建全新prefix，并通过runtime validator、
`pip check`和冻结executor `verify`；聚焦测试集、ruff和diff-check也通过。该实测尚未回写
冻结environment-successor config，所以其中receipt gate仍为false。随后同一fresh v2环境已通过
solver preflight，preflight manifest SHA256为
`aa765cf39ac4d8bc4c279128041764397eb7dcef6a76242fc0e29327d0ed903f`。four-block pilot亦已执行，
但按冻结v1 comparator失败；后续门见下一小节，全部formal execution/result/claim门仍为false。

#### RQ2 cross-solver pilot observed-diagnostic semantic successor（2026-08-27）

冻结v1 pilot已完整结束，result manifest SHA256为
`08a1f2c6808aa03b9601d20252421fb15a03c2d6686540b8b7d04b1cb4c52e90`，transfer archive与
manifest SHA256分别为`701159a2a4bb55cb16837f14ccdebd473e5099145650c4d56fc87c82da9c21fc`和
`be8df8e3ac0bb879fc3a4faf40707ef1bd5b618272ced799e8edf5e6e71c5b30`。原冻结判决为
`268/280 PASS`、`failed_check_count=12`、`gurobi_eligible_for_formal_successor=false`，必须保留。
四项失败来自`holdout_s20260822_0013`的跨solver baseline bound/gap数值相等要求：两solver
incumbent均为`2468277.734686382 USD`，HiGHS合法区间为
`[2468275.8605400943,2468277.7346863793]`、own relative gap约`7.5929e-7`并已accepted，
Gurobi区间退化为`[2468277.7346863784,2468277.7346863784]`且gap为0。另八项失败来自E0 blocks
`0089/0150`的raw status枚举相等要求；两solver均以`termination=infeasible`、primary与zero-DC
`proven_infeasible=true`、`resolved_for_pipeline=true`形成相同E0语义，但Pyomo raw status分别为
HiGHS `error`和Gurobi `warning`。该观察只诊断比较器把solver-specific representation误作跨solver
相等对象，不自动证明Gurobi formal资格。

采用“semantic normalization + fresh confirmatory pilot”，不采用只读reassessment直接开门。
versioned successor锁定全部v1 config/runner/test/result/transfer/handoff/activation SHA；最小化MIP门
改为合法`[LB,UB]`、incumbent一致性与各solver own-gap acceptance，沿用已冻结的`1e-4 USD` incumbent、
`1e-5 MW` finite-grid和`1e-6` residual/solver-gap值，不按结果放宽阈值。raw termination/status原样
保留，仅按solver/version显式映射semantic state；timeout、unresolved、未登记raw组合、缺失/不完整证书
一律不得形成infeasibility或confirmation。纯读validator已在冻结v1上得到
`diagnostic_semantic_consistency_observed=true`，同时固定`v1_eligibility_changed=false`、
`confirmatory_pilot_executed=false`、`cross_solver_confirmation_completed=false`。

successor config/validator/test/manifest SHA256分别为
`cb0209a9a53962be8ebb6ee185d3bfbf3d004d7cd761e164b286a58e0c7887b0`、
`01b7f60a620c81a7a656ba6576c3b85af9e371b30d42dd5959f430ee220c80dd`、
`0137c3dfe6c71b183893dae1007f3e782eceec6030babb5a77dad8cc27c78584`和
`c0b1a6a3074343ab5f281b268cd40898630ad1e2234830a4536189687832f471`。独立R3审查要求的
focused REWORK已实现；同一验收项再次REWORK后，R3升级修复新增hourly finite同记录
`grid_need/incumbent`一致性与逐小时跨solver `[LB,UB]`重叠门。baseline区间仍只用
`rel=abs=1e-12`；hourly solver-report数值包络为`rel=1e-12`与`abs=1e-10 MW`，其中绝对上界
按冻结`model.tolerance_mw=1e-6 MW`的`1e-4`机械定义，且仅为跨solver `1e-5 MW`科学差异阈值的
`1e-5`。该上界透明标记为v1观察后的诊断合同，不能重判v1或代替fresh confirmatory pilot。
冻结block role、24小时source-hour顺序及event/component逐项绑定；残差强制非负且active finite/E0
模型规模为正；v1/v2 bundle、outer、input package、preflight、pilot result、transfer与tar成员均做
精确inventory及live-byte验证。上一轮独立`sol_reviewer`以`ESCALATE`指出hourly `abs=1e-10 MW`
曾被误传入整个`_certificate_interval`，会接受`5e-11 MW`伪造absolute gap与反向区间；该历史保留为
必要审计事实。用户已通过持续目标授权机械修复：certificate内部区间方向、gap重算、
incumbent-in-interval和own-gap一致性全部恢复为`rel=abs=1e-12`，hourly `abs=1e-10 MW`仅保留在
same-record `grid_need ↔ incumbent`和pairwise interval overlap两处，并新增两项`5e-11 MW`
fail-closed对抗测试。29项聚焦测试、72项相关回归和0 solver/0 write纯读validator通过；该机械修复
已由独立`sol_reviewer`复审为`PASS`，review receipt SHA256为
`1be79d21ac6f554b742d929b53e84c8e1c35c25bc8ccadaf78d76cf2cf5912b8`，原v1失败判决不变。

fresh confirmatory v1的versioned config/runner/validator/test已实现，SHA256分别为
`c78bd3b901fdf9ff8dc1cc66c9adda6156ed1f889d3cc37a5870021b38ac3975`、
`9f09327acb31b9ab174918a011a2fa0902e206731e898b8b150a6bbdc7eab007`、
`7a4ab4e2afa9ffeabd3895d0152cb3bb7f438b06005058998257a70196064c7b`与
`3ef675cbb8163304ad72c3ba6450797e7bd7d524b0b93360d265c6f43b599222`；bundle/outer SHA256为
`ea3957c0ee3dd01f34efd6112db88fbfdec982e026aaec65e4780599db76dfe2`与
`3bea21c2e1905d7a930c80da0dbf138cd130d85c221e436e961eb8965074205f`。controller自身不调用solver，
按`highs_r1→gurobi_r1→gurobi_r2→highs_r2`为每个run_id启动fresh独立Python subprocess；每个worker
只向注册的独立temp root发布单run payload，父进程逐项验证parent/config/implementation hash、实际
PID/parent PID、exit code、ordinary non-symlink、exact inventory/schema/hash及run identity后聚合，
再调用已审`evaluate_runs()`，只以同卷staging原子rename发布全新
`results/tables/rq2_public_solver_confirmatory_pilot_v1`。2026-08-28用户“继续做/按路径全部做完”的
activation SHA256为`b28a8254d93e8173e5cd9e62ad0200735ad6d3813b45401e42037266bc8ccc3f`，仅授权
confirmatory；watchdog为21600秒，solver `time_limit=null`，grid/pairwise/identification/formal
claim/security均未授权。23项新增focused tests、95项相关联合回归、ruff及canonical 0 solver/0 write
preflight通过，preflight只置`implementation_ready=true`。该confirmatory实现仍待独立R3审查，配置
中的实现审查门和`execution_ready`均为false，本轮未运行solver且结果目录不存在；因此
`confirmatory_pilot_executed=false`、`cross_solver_confirmation_completed=false`，此前
grid/pairwise/identification及所有formal/result/claim/certification门保持false。解除cross-solver
blocker的最小后续条件是：本实现独立审查PASS并由versioned后继打开该单一执行门；fresh pilot完整
manifest通过同一语义门；再由独立审查和新的grid activation authority决定是否开启grid。

独立R3对confirmatory v1实现给出`REWORK`后，整改只进入新的v2审查候选，v1及semantic predecessor
字节保持不变。v2持久化controller PID/start/nonce receipt，以及每个run的worker payload和controller在
exit 0、实际PID/PPID、schema/hash验证后签发的receipt；逐run证据绑定run/solver/repetition、execution
index、config/runner/semantic authority、payload SHA和exit code，并以递增签发时刻及previous-receipt
SHA形成顺序链。validator从payload按冻结顺序重建`runs.json`，严格拒绝duplicate-key/非标准JSON、
PID/PPID/nonce/hash/exit/order漂移、extra/missing/symlink和非精确recursive manifest。该provenance仅是
执行期controller观察，不是外部OS/硬件鉴证。`evaluate_runs()`只有在schema、4/16/384/24计数、raw
status inventory和四个关键布尔字段全部精确成立时才允许fresh wrapper置
`cross_solver_confirmation_completed=true`；timeout、unresolved和不完整证书仍不是不可行证据。

v2 config/activation/REWORK receipt/runner/validator/test/bundle/outer SHA256分别为
`d0a5c3a898d89ce869a6647b4d8f271f82921c89069cdd9dd98b4f54e7c9f1e0`、
`fd4e584b86de791f014e417499fa14c7db7de07f4e6e63adb8270b879c39a45b`、
`4e06fefc95addda419d8e721e2be6963a685ee3c6e136acf36efc3c2d1cc5c13`、
`59a54f9fb1c987baffe0a12a11d9584081da7bd8db60800b4fe0fc0da6a43eaa`、
`605936ccca949d9f022b7b29c9b96738a43f72a6b2072a4bfecf277b31412e4f`、
`9b19e3f4be515d9a6c20380326efd21761f9268d735089567c72f3de34c4e1d7`、
`b356dfa1d58eeb416cbe81d6d840142d4e676b296d39a7372825f7f1d5cc6687`与
`601c10c53daa80661db39fd356a7987dce58dcf4ce98bf9c77197f71eb448490`。在下述独立复审结论到达前，当时只允许使用
`RQ2_EXECUTOR_PYTHON_EXE`指向的绝对普通Python运行canonical
`python -m experiments.run_rq2_public_solver_confirmatory_pilot_v2 --validate-only`；v2审查前门保持关闭。
只有新独立`PASS` receipt精确绑定封口v2后，才可新增完整v3八件套并以
`python -m experiments.run_rq2_public_solver_confirmatory_pilot_v3 --validate-only`预检、随后用同模块无
`--validate-only`执行fresh confirmatory。这是复审前的历史预案，已被下述`ESCALATE`作废，不是当前执行授权。

独立复审随后对v2给出`ESCALATE`：post-result validator曾以receipt内嵌`worker_report`本身构造expected
report，故最后一个receipt的嵌套`run_id`、嵌套SHA和总manifest可被同步伪造而不触发拒绝。这是同一
durable provenance验收项第二次失败，v2与v1/semantic predecessor均保持原字节。v3 remediation
successor精确绑定v2 outer
`601c10c53daa80661db39fd356a7987dce58dcf4ce98bf9c77197f71eb448490`及全部v2八项SHA；当前不授权执行。

v3的live/post-result共同调用纯函数`build_expected_worker_report`，只从注册run身份、实际payload、
controller receipt、payload SHA和live `Popen.pid/returncode`或post-result zero-exit合同重建exact report。
嵌套report必须exact equality，其SHA也从重建值计算；最后receipt的run/solver/repetition/PID/PPID/
controller identity/config/runner/semantic/payload SHA/exit/order代表项，以及顶层/嵌套extra/missing/
duplicate-key对抗均fail closed。validator继续从payload重建`runs.json`。

v3 config/activation/ESCALATE receipt/runner/validator/test/bundle/outer SHA256分别为
`3f7a1fd1e93ec46a608e8cd164abb685365fd04d4575a7f8890f0832791415ca`、
`da07e16c7bca60a44c97803bd60919a6f9f3a83042da58065af4c5a7836763e9`、
`4561e17bf16f89a33efbde0b5cc9eee706bf53c82712dee6258bae5e451796d9`、
`7dd844ab96cb1db8c20a945d6ba60ec5133469a9e66b3d5d8200d792b9d1f7bf`、
`7cd52649133d97ab7e06c8f72d3fd3334227e2346b4bb633873a530c96909877`、
`46fc54b090f2cd7de36310421a7b7418df9fc6d58d6b8931815e76bb77b986c0`、
`d393c33b037457250eb14e5263dabc6277d6c9b9bd6a9e3697bf2c38b321c8a5`与
`d7b8b7dd2cf0bc51f46602c1c7e28c1aad281c977ff8a15b0617be392e4a2f49`。当前canonical命令仅为
`python -m experiments.run_rq2_public_solver_confirmatory_pilot_v3 --validate-only`，41项focused与166项
相关回归通过，0 solver/0 write且结果目录不存在。独立v3 review与v4 execution successor仍缺失；只有
全新`PASS` receipt绑定封口v3后，才可新增完整v4八件套打开单一confirmatory门。grid/pairwise/
identification/formal/security继续关闭。

#### 增强基线鲁棒性设计门（2026-08-25）

`rq2_public_baseline_robustness_preregistration_v1`只冻结四臂 successor 设计：
`network_only_shared`、`cfe_only_shared`、`joint_correct_shared`与
`joint_b6_separate_planning_shared_execution`。它逐项继承 v4/v6 的公开数据、
15 个 OAT cells、block splits、训练代表点与完整支持审计、fixed-policy holdout、
时序物理包络及 solver contract；不得按已观察的 70-cell 结果改变参数或阈值。
既有计数继续为`R1=0,R2=0,R3=69,mixed=1,unresolved=0`，原正向 H2 仍不支持，
且 v1 pilot已观察但原比较器失败，semantic confirmatory pilot与formal result仍未观察。

该设计要求 full-transport primary、multimetric 同一 coupling witness、E0 单列和
fail-closed 互斥归因；机制标签只读取capacity contrast、failure probability与
expected shortfall，正recovery debt及right-censored terminal debt仅作描述。
T1 MW-only只作解析诊断，现有pairwise v4缺少所需原始`g_t/c_t`轨迹。结果链首阶段
已精确绑定v6现有grid v4 config/runner/direct implementation/output/schema，但尚无
runtime receipt/provenance且`ready=false`；只有后三个four-arm future stages的
implementation/config/runner/output为`null`。
`implementation_bound=false`、`independent_R4_review_passed=false`、
`user_formal_run_authorized=false`、`formal_execution_ready=false`、
`formal_result=false`。解除本门至少需要 versioned 实现与 schema 冻结、独立 R4
复审、用户正式运行授权，以及四阶段 provenance/checkpoint/witness/manifest
完整验证；本 preregistration 不接入现有 executor。
冻结config与manifest SHA256分别为
`017708b25c3e1702c938a108af070a7047517bd128552500d3ffcac6a3ee3554`和
`da6d13055ccfcd03c00939ab7fa61f43e05052556211f725b4550a09d33f64c9`。

2026-08-26新增的R3 core只实现四臂不可变call projection、同一solver contract下的
minimum-flexibility planning、finite-grid shared-envelope causal replay和完整training
support audit。network/CFE单服务各自清零另一类call；joint-correct使用共享规划，
joint-B6仅在规划审计中分开检查两条包络，执行仍共享。E0在产生pair outcome前拒绝；
timeout或未决异常不转写为infeasible。core另输出版本化的registered service-risk
outcome：service shortfall与非debt、已注册的physical violation可触发failure；v1尚未
绑定的debt-limit/terminal-condition violation、raw debt和right-censored terminal debt
只保留为可追溯诊断，未知physical violation保守计入failure，raw flag与violation清单
不一致则registered outcome为unresolved。
现已另增versioned public checkpoint/package core与validate-only successor：它绑定冻结
prereg manifest和v4/v6 authority，提供planning/finite/E0 checkpoint、resume identity、
partial no-publish、不可覆盖publication及exact manifest合同；successor config/manifest
SHA256分别为`2d7a801b2cc0b078650a6b9917a45d282a3d9f273a0eb6043361a89a6c5f7d9a`和
`0234ed0eb54b30f15891ff49df7f74fea678e6f05309a8c1e4473a9ea7d34954`。合同现逐项验证
checkpoint/final provenance、各arm planning joint-budget语义、finite pair容量与同cell
planning minimum的精确绑定、raw到registered v1语义、全cell Cartesian marginals与
E0公共mass、完整training pair inventory hash，以及symlink/Windows reparse路径安全。
该增量不是完整
external-data runner/identification/report orchestration，未产生runtime结果，也尚未通过
独立R3/R4复审；`implementation_bound=false`、`ready=false`及全部执行/结果/claim门
保持不变，冻结prereg中的future paths/hashes仍为`null`且字节未改。

2026-08-27新增独立的entry successor v2，只补齐external preflight与computation runner
implementation。当前只读preflight确认workload v3为34/34个24小时block；grid输入则分别
登记为冻结authority gate为false、package缺失以及manifest/config/provenance hash为null，
不把这些状态解释为E0或infeasible。future ready分支要求grid package恰为8个普通成员、
1071个checkpoint key且provenance/inventory/summary交叉hash一致。实际入口在任何mkdir、
lease、checkpoint或solver调用前依次要求live config/manifest、external preflight、四个
独立执行门及host授权；resume identity绑定config、全部上游authority与training/holdout
inventory，partial pair前缀只返回no-publish progress，异常或unresolved planning不产生
final package。config/manifest SHA256分别为
`26a91ac203c228555402f09751c6560d356dc860eedf5d681454cc2cdcb68cab`和
`120421396bbea022d9bc939a7a5d39e2d1f70c1eaa40c14bf78b5417d1510514`；纯读validator
验证21个文件且solver/result write计数均为0。该实现未运行solver、pilot或formal，未产生
runtime result，冻结v4/v6、prereg及package successor v1均未改；独立复审及四个执行门
仍为false，故`implementation_bound=false`、`ready=false`、`formal_result=false`、
`claim=false`不变。

2026-08-27新增validate-only identification/report successor v1：纯adapter只接受通过
canonical package v1验证的六个schema，逐cell重建E0分离后的共同marginals、14个注册判定
estimand、scalar endpoint primal/dual证书和exact common-π分支，并保持debt仅描述、right-censor
不转写为failure。六schema在两次canonical package验证之间按bytes/hash稳定捕获，live manifest
与成员漂移均fail closed。report build/validation不再信任standalone payload中的bound view、
common-π status、debt证书或provenance；必须同时提供canonical upstream package目录和manifest
SHA authority，重新识别完整payload并exact compare后才重建report，且report绑定identification
payload、upstream manifest和provenance三个SHA。无package/payload authority一律拒绝；
synthetic document seam不是public validation authority。config/manifest SHA256分别为
`0bfa8e9fc08204c294fc160744ef208ab6bafeb32982f6912d89908c07970579`和
`2eca13d94c904372b320d1892f139a58ff26d6830ef21cc0354430c7806cf673`。T1所需raw `g_t/c_t`
仍缺失且path为`null`；上游package、activation、输出与全部执行/result/claim门仍为false，
未运行真实identification或发布report。2026-08-27 implementation-only R4已`PASS`，原三条
对抗绕过均已拒绝；冻结config中的machine `independent_review=false`仍不变，因为当前没有
独立machine review receipt或activation authority。未来真实upstream package、runner或publisher
必须由新successor绑定manifest SHA并重新完成R4；本次`PASS`不授权formal run、report或claim。

2026-08-28 RQ2 confirmatory successor 当前状态补充：v3 remediation 的八项 predecessor
字节仍由 v4 精确绑定（v3 outer SHA=`d7b8b7dd2cf0bc51f46602c1c7e28c1aad281c977ff8a15b0617be392e4a2f49`）。
v4 八件套已完整落盘并通过 live-byte 复核：config SHA=`8d23066e30e01cdcb54fb502aaf654548c44c0c9eb7d182d52b7f4e4f992bb48`、
activation SHA=`1223f89b63e7860f64ce8a6447aefe6343f7db149a4c3ffef63369235d51e1a9`、
implementation PASS receipt SHA=`2b60e856e87a6ce0a27c2a2bb04996d1755ef81c10208d944a7721c2f0445b24`、
runner SHA=`88835bb66fb168bc89feff0f124e00e29da7a0792e57e9101719cf7a2b591671`、
validator SHA=`78e71e60b3daead7daa39bea32556eac7c9e6e61375c2952337462dadc56fcd6`、
tests SHA=`acf0d4a6c0bf800d32fda656dc46fad1efbcdfabb6fa60b8530740b2e9271687`、
bundle SHA=`8e1c441b51b3f4d5911e3d9350bf552289bba6720ac279171d24a797fa57b7ab`、
outer SHA=`983c71b98062a3676c0abe9bee9020bf901a1f5a5a02b82fffba833310a84d44`。
v4 focused pytest 为`9 passed`，Ruff通过，canonical `--validate-only` 为
`validation_passed=true`、`implementation_ready=true`、`execution_ready=true`、
`solver_calls=0`、`result_files_written=0`、`result_present=false`；formal/result/claim/security
门均为`false`，fresh pilot 尚未执行。

截至当前独立 `sol_reviewer` 复核对 v4 仍为`REWORK`：发现 blocker/执行计划的当前状态记录滞后，且
activation 内部 artifact binding 与执行环境复现证据需要补齐。故上述 v4 配置中的候选执行门
在完成文档同步、锁定执行环境复核并取得新的独立`PASS`前，实际执行门保持关闭；不得启动
solver。复现环境固定为`D:/conda_envs/rq2-executor-v2-audit/python.exe`（PyYAML`6.0.3`），
系统默认 Python 缺少`yaml`不能作为 canonical executor。完成整改后仅允许按 activation
执行一次 fresh v4 confirmatory pilot；`grid/pairwise/identification/formal/claim/security`
继续关闭。历史 v1/v2/v3 与既有 pilot 结果保持不可变。

2026-08-28 最新独立 `sol_reviewer` 复核结论为`PASS`。复核确认上述 v4 八件套最终 SHA、
bundle 六成员、outer bundle 绑定、v3 predecessor 不变性、锁定 executor 环境、聚焦测试、
Ruff 和 canonical `--validate-only` 均一致；`validation_passed=true`、`implementation_ready=true`、
`execution_ready=true`、`solver_calls=0`、`result_files_written=0`、`result_present=false`，
且 v4 结果目录不存在。故此前 REWORK 段仅作为已解决的历史状态保留；当前仅打开一次
fresh v4 confirmatory pilot 执行门，`grid/pairwise/identification/formal/claim/security`
继续关闭。pilot 完整 manifest、四个 run 的 provenance 和 semantic evaluator 通过前，
`confirmatory_pilot_executed` 与 `cross_solver_confirmation_completed` 仍为`false`。

2026-08-28 fresh v4 confirmatory pilot 已按 activation 完成，且只运行了注册的四个 run：
`highs_r1`、`gurobi_r1`、`gurobi_r2`、`highs_r2`；四个 worker 均 exit code 0、PID 唯一且
parent PID 均绑定 controller PID。结果目录的 `SHA256SUMS.json` SHA=`70003e18566c208631768dd028d573cd0c5e45d4f8fb0e7104ec1f1158d98a58`，
`summary.json` SHA=`5d32dd9636c43ea431b9998cd566bd7e4eb6d6a5ea6d7331655dbb862069a3e2`，
`semantic_validation.json` SHA=`ee644933695b0749363f75e227fd3f4201d1f68da57900cd9097d2c378dd0399`。
post-result 机器证据与独立审计均确认`fresh_execution_passed=true`、
`durable_process_provenance_verified=true`、`nested_worker_reports_reconstructed_independently=true`、
`runs_reconstructed_exactly_from_worker_payloads=true`、`semantic_contract_passed=true`、
`cross_solver_confirmation_completed=true`；`formal_grid_execution_started=false`、
`formal_result_exists=false`、`claim=false`、`security_certified=false`保持不变。该结果只确认
非正式 cross-solver confirmatory pilot 的执行证据，不构成 formal result、工程安全认证或论文
claim；post-result R3 审计完成前不推进任何后续 grid/pairwise/identification/formal 工作。

2026-08-28 post-result 独立 `sol_reviewer` 审计结论为`PASS`。复核确认结果目录 13 个成员的
精确递归 manifest、`SHA256SUMS.json`、summary、semantic_validation、controller receipt、
四个 worker payload/receipt/report、PID/PPID/exit、previous-receipt 顺序链和 runs 重建均一致。
wrapper 顶层`cross_solver_confirmation_completed=true`可作为本次非正式 pilot 的执行证据；
semantic evaluator 内嵌的历史 diagnostic `cross_solver_confirmation_completed=false`不改变该
wrapper 结论。当前 pilot 层`confirmatory_pilot_executed=true`、
`cross_solver_confirmation_completed=true`；`formal_grid_execution_started=false`、
`formal_result_exists=false`、`claim=false`、`security_certified=false`继续保持。该 PASS 不
授权任何 grid/pairwise/identification/formal/security 后续工作，后续阶段必须重新取得对应
versioned activation 和独立审查。

### v4 grid正式attempt的运行性中断与恢复授权（2026-08-29）

`rq2_public_grid_need_activation_v2`及独立grid activation review通过后，v4 Gurobi grid正式
attempt已启动并原子发布`holdout_s20260822_0000`--`0008`共9个checkpoint。9个文件均与当前
activated config的`stage_base_provenance_sha256=d6d4b69df6c212c0b79c4bb99e7f518305b626bf82a3b1198da4a6306c95442f`
一致，216/216小时均resolved且残差低于冻结`1e-6`；正式output尚未发布。Windows System日志
确认进程在2026-08-29 16:48因用户发起整机重启而停止，不是solver crash、timeout或数学不可行
证据。当前runner允许精确复用该9-block前缀，并从`holdout_s20260822_0009`重新求解。

同一block此前两次进程的虚拟内存占用约23--27 GB并触发Event 2004低虚拟内存警告；重启后
host总commit仅约30.38 GiB。用户现已明确授权调整pagefile、重启并恢复正式实验。恢复候选仅
增加host级commit容量和一次性fail-closed启动/30分钟监控，不改变冻结config、solver参数、
stage identity或checkpoint内容；在pagefile实际生效、总commit不少于64 GiB、authority hash、
9-file prefix、host gate和canonical `--validate-only`全部重验前不得调用solver。pairwise、
identification、formal result、claim及security门继续关闭。

### v4 grid `0009`恢复暂停并转入根因诊断（2026-08-29）

用户随后明确要求暂停pagefile/配置缓解路线，先定位并修复`holdout_s20260822_0009`的根因。
因此上节恢复候选已被当前指令暂停：当前没有相关formal或diagnostic进程，不启动/恢复正式
runner，不改pagefile、冻结YAML、solver adapter、SCUC模型、9个checkpoint或正式output。
此前创建的pagefile恢复脚本不是当前执行authority；是否保留或撤销须另行处理，不能据此自动
恢复实验。

已新增完全隔离的development diagnostic入口
`experiments/diagnose_rq2_grid_need_gurobi_block.py`。它只调用activated v4 runner的normal-SCUC
路径，默认顺序比较邻接control `holdout_s20260822_0008`与target `0009`；除诊断性
`TimeLimit/tee`外逐项保留正式gap、tolerance、seed和threads，并在独立子进程中记录Gurobi
原生日志及Windows `PrivateUsage/working set/system commit`。table/log root与formal
checkpoint/output任一包含关系均被拒绝，运行前后逐文件SHA-256必须一致；另有private-commit
上限和system-commit reserve，资源停止固定标记为`diagnostic_resource_stop`且不得解释为
不可行。

首次独立R3审查给出`REWORK`：隐藏worker曾可把`--worker-result`指向formal目录，顶层
`--gurobi-probe-profile`也未贯通controller child。唯一一轮聚焦修复已使worker在任何payload
写入、data load或solver路径前按activated config复验formal checkpoint/output隔离并拒绝覆盖；
profile现完整绑定CLI、controller、child command、worker receipt与summary。11项聚焦测试及
Ruff通过；同一`sol_reviewer`复审为`PASS`。当前诊断runner SHA-256为
`f254fcc602af0faa7538335661c6a8d27d21b4fe6f1506ba27290eb6f477eb97`，测试SHA-256为
`4b4b46c56c26acee2c64aaf8f08c8f0dd7896040533cac06fd166f539a77ef6f`。

审查前5秒root probe v1已持久化于
`results/tables/rq2_grid_need_gurobi_0009_root_probe_v1`和对应logs。结果manifest SHA-256为
`d44f1fbe162b8e0f082fa36ef3bfed02aa648e1e9e16523836e7bebb49551ae8`，summary SHA-256为
`b50effaedcb1a938577b212e33ca86a99a64c9423dd1aeea6d814f27b648bf0a`；formal 9-file
checkpoint集合及每个SHA在运行前后完全相同，formal output仍不存在。相同模型规模和冻结
科学参数下：

- `0008` root relaxation为`2050015.61 USD`，首个incumbent gap约`0.18%`，最终在`4.54 s`、
  1个node内闭合zero gap，peak private bytes为`496877568`；
- `0009` root relaxation为`1809916.44 USD`，5秒时最佳incumbent仍为
  `1864843.625132 USD`、best bound为`1810048.133884 USD`、gap=`2.9383%`，同样只探索
  root node，peak private bytes为`495284224`；无numerical warning或OOM报告；
- 历史v3 HiGHS同一`0009`证书已有UB `1813595.3686598851 USD`、LB
  `1813593.9879859171 USD`、relative gap `7.61291075098e-7`。故短探针支持“Gurobi在
  `0009`的早期incumbent/search path显著劣化”，不支持不可行或root数值故障；5秒尚未进入
  大型node tree，不能单独证明23--27 GB来自node storage，也不能证明native leak。

v1数值使用`formal_default`，故旧profile传播缺陷不改变其数值，但其summary绑定的是审查前runner
SHA，只能作为历史diagnostic，不能声称由当前runner fresh复现。修复后root probe v2的manifest/
summary SHA-256分别为`8c75caae1f8deae001e1762767cbc69c64fc6ebc47955b9ddd686b1dcef7be88`和
`5f8555ff1fd6e27bcab1079894ea7a2c902df13bd7ae4577f25f762c3efa50d0`，与当前runner SHA一致。
由于host commit继续下降，两个child都在已记录`solver_started`、Gurobi启动及`Optimize a model`
之后、产生node progress或final certificate之前触发`system_commit_reserve_reached`；均为
`diagnostic_resource_stop=true`、`worker=null`且
`solver_infeasibility_inferred_from_resource_stop=false`。v2只验证当前runner的安全停止和formal
哈希保护，不替代v1数值证据；formal 9-file集合/SHA仍未变化，formal output仍不存在。

模型中73台committable units有56台落入24个同址同参数组，最大组5台；identical-unit
symmetry是高优先假设，但后续corrective LP按具名outage UID及具名baseline dispatch/
commitment运行。因此即使solver symmetry option保持normal-SCUC可行集与主目标，也可能改变
下游具名事故结果。任何正式修复必须先证明组内重标号不改变目标estimand/输出，或建立与未来
事故信息独立、预注册的确定性tie-break；不得恢复会删除合法crossing trajectories的逐时
commitment ordering。

解除当前诊断门需要在安全host commit下完成fresh `0008` control与`0009` target长探针，取得
node backlog、bound/incumbent与private commit同步轨迹。当前host有无关交互进程占用约
9.45 GiB private commit、可用virtual/commit约1.4 GiB，低于诊断默认2 GiB reserve；未经用户
授权不得结束该进程，长探针必须fail closed。`0009`根因和最小语义保持修复经R3证据及独立
`sol_reviewer`审查前，不得恢复正式run。
### 2026-08-30 grid recovery v1 REWORK 与 process-isolated v2 闭门候选

`holdout_s20260822_0009`的 Gurobi `formal_default` 900 s 诊断和
`bound_focus` 1800 s 诊断均以 `TimeLimit` 结束；两者均为 diagnostic
unresolved，不是数学不可行。HiGHS fresh-child acceptance 对 `0008/0009`
的 normal baseline 均通过，但该入口只调用 `_normal_baseline`，没有运行包含
逐小时具名 outage corrective LP 的完整 `_process_block`。因此该证据不能外推为
原 v4 同一 Python 进程内连续处理 1071 blocks 的 formal route 已获支持。

recovery v1 已由独立 versioned receipt 登记为 `REWORK`（receipt SHA-256
`cfe8d1f5fb7cef9514ab995b19b20bed43f3604af5ad84ab6433ae84a9810834`）；
v1 preregistration、原 v4 runner、冻结 Gurobi config、9 个 checkpoint 和既有
diagnostic 结果保持原字节。新的 v2 只冻结 execution-topology successor：每个完整
24 h block 由一个 fresh Python worker 执行，worker 只能写隔离暂存结果；parent
不调用 solver，在 PID/PPID、nonce、Python、config/stage、block input、parent/worker/
v4 core/grid adapter/solver adapter/resource guard hash、solver contract/options 和完整
科学 payload/certificate 全部通过后，才将 checkpoint 与 execution receipt 作为单一
JSON envelope 原子发布。resume 只接受从 block zero 开始的连续新 schema prefix；旧 v4
checkpoint、hole、extra、duplicate nonce/request hash、unresolved、timeout、resource stop、nonzero exit、
缺失 payload/certificate 均 fail closed，且不形成 completed checkpoint 或 infeasibility
结论。当前 child 仍须通过 PID/PPID 身份校验，但 OS 合法复用历史 worker PID 不得阻断
resume。finalization 仅在精确 1071 个全部 resolved 的 inventory 上开放。

v2 preregistration/config/provenance/runner/validator/tests/manifest 当前 SHA-256 分别为
`a767708dfd1bcb243df9d0466a092a7d7cf090c6583af162119e72cadc919e59`、
`e1306a375bba5d19d687cb2728a981528662064226b4661a0b74f894b647f3bd`、
`cb6ae7c07a7745f90288cefafedb7df82221d06205b3d2aab68580e0587a89b1`、
`c90f796aa9c9043d48560599b892681455b7c7ddee3881501ce449bfa1c3833e`、
`cf563d95ea024b38587350cfae73af0c597d8d491544e2306def214b7a296fe1`、
`56eb993a3ad3856447690776b3d8a6f7ef08faad04a1fc85744f2004546561bb`和
`b300a040fc481beea094702404f4d00eb176403e40f7909d2d704f7fd2195729`。
focused v2 tests 为 `31 passed`，v2+v1+diagnostic 相关回归为 `52 passed`，Ruff 通过；
canonical validator 为 0 solver、0 result
write、0 formal write，但明确报告 `implementation_ready=false`、
`execution_ready=false`、`formal_execution_ready=false`。当前没有 activation 文件或
执行授权。首轮独立 R4 给出 `REWORK`；第一轮聚焦修复的复审发现小于 tolerance 的
`LB>UB` 会被接受，同一验收项再次失败后给出 `ESCALATE`。用户已明确授权第二轮
聚焦机械修复：certificate 与 baseline 现在均先严格拒绝任何 `lower>upper`，仅在方向
合法后以 `upper-lower` 重算 gap；有界容差、solver/model 和其他科学语义未改。该用户
第二轮修复的独立 re-review 随后发现 `absolute_gap/relative_gap/gap_tolerance` 及
baseline `configured_mip_relative_gap` 仍经 `_close(abs_tol=1e-9)`，会接受 `-1e-30`或
`+5e-10` 伪造漂移，故第二轮 re-review 保留 `ESCALATE`。用户已仅授权第三轮
derived-field 机械修复：上述字段先做类型、finite/nonnegative 校验，再与 bounds 和冻结
config 机械重算值作零容差相等比较。该授权不是 formal-run 授权，
`user_formal_run_authorized=false`不变。当前仍等待独立 re-review，不得视为 `PASS`。
解除本 blocker 必须依次取得：独立 R4
implementation `PASS`；以完整
`_process_block` 对 `0008/0009` 执行的非正式 two-block pilot；相对冻结 Gurobi `0008`
checkpoint 的具名 outage 输出比较；pilot post-result 独立 `PASS`；最后才可由新的
versioned activation authority 开门。任一门失败都不得启动 formal run，所有 formal/result/
paper-claim/security 字段保持 `false`。

### 2026-08-30 recovery-v2 implementation PASS 封存与 two-block pilot 闭门候选

上节“独立复审尚未通过”是 candidate 封口时的历史状态。第三轮聚焦修复现已由独立
`sol_reviewer`复审为`PASS`，并以新的 machine receipt
`configs/rq2_public_grid_solver_recovery_implementation_review_pass_v2.yaml`封存；receipt
SHA-256 为`3153d72000fb7ea87f55adc3eed63af5fdb0901a48ded6ae92a616924088c720`，精确绑定
recovery-v2 bundle SHA-256
`b300a040fc481beea094702404f4d00eb176403e40f7909d2d704f7fd2195729`及其 7 个 live member
hash。该 PASS 只关闭 implementation review，不授权 pilot execution、formal run、论文 claim
或 security certification；不可变的 recovery-v2 prereg/config/runner/validator/tests/manifest
字节和其内部 closed gates 均未改写。

用户已明确授权在独立 pre-run review 通过后执行一次`0008 -> 0009`非正式 two-block pilot，
但本轮只建立不可执行的 versioned candidate。candidate config、user activation、runner、
validator、tests、inner bundle、outer manifest SHA-256 分别为
`89316d2f8de8ac43f84d615b2bb75f7ff6820b415b67c5ba2be27cd04194ef61`、
`03927d1dab6eaf18722900a0e1f225f675671ac2c01984edd5f04d6a9251f79b`、
`f468d960768650b931d3b2bbc226642576807e393f216d2b9f1dde51b707b452`、
`05e34709e2cab90241f1c135382d363c55cd58757621905cafd7220c22fe35eb`、
`164cf437c0616fcdf7a6bc137fc5e1021f7bef89ce253c570f76109629b69f50`、
`cdb70f0dc87eff25f0d2082d207bddfacb4701c75042065f1aa06e38a6a5fb15`和
`7874a9bdb83d36de98e7626bbe259fd607f1d9d2f8e5669e9924c6f84a02306f`。
config 不回指 inner/outer digest；outer 只绑定 inner manifest，故没有 hash 循环。当前
`independent_pre_run_review_passed=false`、`execution_successor_present=false`、
`two_block_pilot_execution_ready=false`。controller 与 hidden worker 均在 scientific
preflight、data load、`_process_block`和任何 solver call 前由该三门 fail closed。

candidate 完整继承并 hash 绑定 recovery-v2 的 HiGHS 1.15.1、4 threads、seed 0、
`time_limit=null`及原 tolerances；每个 24 h block 预注册一个 fresh Python child，external
watchdog 为 21600 s，private commit 上限为 8 GiB，system commit reserve 为 2 GiB，采样间隔
为 5 s。具名 outage 比较只允许新 HiGHS `0008`对冻结 Gurobi `0008`：两侧先分别通过完整
payload/certificate gate，再要求 block/hour/event/component/state 与 model scale 相同、finite
grid need 差不超过`1e-5 MW`且证书区间相交、baseline incumbent 差不超过`1e-4 USD`且区间
相交、E0/zero-confirmation 语义一致；不要求 raw status、LB、absolute gap 或 gap tolerance
跨 solver 逐字相等。`0009`只要求完整 process/payload/certificate，不与不存在的 Gurobi
`0009`证书比较。missing、unresolved、timeout、resource stop、nonzero exit 或比较失败均不会
生成 success result，也不推断 infeasibility。

focused candidate tests 为`15 passed`，recovery-v1/v2、diagnostic 与 v3-runner 相关回归为
`57 passed`，Ruff 通过；canonical validator 返回`validation_passed=true`、
`pilot_implementation_ready=true`、`execution_ready=false`、`solver_calls=0`、
`result_files_written=0`、`formal_writes=0`。三个新 pilot roots 均不存在，旧 v4 runner、
activated Gurobi config、9 个 checkpoints 及 formal output inventory/hash 保持不变。pilot 尚未
执行。下一步只能由独立 pre-run R4 审查当前 outer；若为`PASS`，再新增独立 versioned
execution successor，精确绑定该 outer SHA 与新的 review receipt，不能修改 candidate bytes。

### 2026-08-30 two-block pilot v1 REWORK 与 v2 closed successor

独立 pre-run `sol_reviewer` 对已封存 candidate v1 给出`REWORK`。历史 outer
`7874a9bdb83d36de98e7626bbe259fd607f1d9d2f8e5669e9924c6f84a02306f`及其七项
live-byte 证据保持不可变；versioned REWORK receipt SHA-256 为
`8fd6f56403c593255ea2e7c36cbfc0c94329af7d716a6f4b336e8f0aff2d4d6a`。问题是 v1
未把 semantic-v1 注册的 solver raw-status normalization、recovery-v2/semantic-v1 全成员运行时
复核、hidden-worker controller/path/PID-reuse 证据和 copy 后重读校验完整闭环。因此 v1 不得执行，
也不得原地修改或激活。

新建的 candidate v2 只修复上述 pre-run implementation 边界，科学模型、solver 参数、冻结比较
阈值、recovery-v2、semantic-v1、旧 v4 runner、activated Gurobi config、9 个 checkpoints 和
既有结果均未改动。v2 明确调用 semantic-v1 注册表规范化 baseline、每小时 primary 与 E0
zero-confirmation：HiGHS 仅接受`optimal/ok`、`infeasible/error`和
`not_applicable_no_active_outage/not_applicable`；Gurobi 仅接受`optimal/ok`、
`infeasible/warning`和`not_applicable_no_active_outage/not_applicable`。任何未登记 pair（包括
`globallyOptimal/ok`）均使比较 unresolved/fail closed，绝不转写为 infeasible。

controller 和 hidden worker 每次进入 data load 或`_process_block`前，均须重验 recovery-v2
manifest SHA 与 7 个 live members，以及 semantic-v1 config/manifest/validator 的固定 SHA；这些
authority 字段直接贯穿 controller receipt、request、result 与 worker receipt。request 另绑定可读且
精确有效的 controller receipt、canonical scientific config/result/worker paths、PID/PPID、Windows
process creation time、nonce 和 request hash；POSIX symlink 与 Windows symlink/junction/reparse
point 均拒绝。controller 复制 worker 证据后，在 atomic directory rename 前从 staging 重读并重新
验证完整 schema、payload/certificate、receipt/payload hash 与全部 authority。

v2 config/activation/runner/validator/tests/inner/outer SHA-256 分别为
`8b8283c59b4200d593c42528ee1792588a2051a00725fcd6f27798050ace0477`、
`91af62a1aba3ab91cbbc3e351374008bcee6eb4de8f774ad6e68bfd1a3740366`、
`b16acb1628ef44cdf3eeb060284e2db4adcf3a0b785c3950bfbc9c7d0c6ac6c7`、
`a6568aced8e5734dc6f396b269df8bef2992a584299435bd0bc56ab8eb69ee38`、
`162e89dcbb30654a758352c4b04a4f117926414e6c09fc6191692a376ef2f6d8`、
`fd7e0d92e78c92991602fe1dcd25c0a20e00fd6bc8f4f927a3431dda816b2598`和
`fb2185a707e905480d6d0fc03b95c178420293807b309459548f99a31f782743`。当前 focused
tests 为`24 passed`，Ruff 通过，canonical validator 返回`validation_passed=true`、
`execution_ready=false`、0 solver、0 result write、0 formal write。v2 三个 execution roots 不存在；
pilot 未执行。当前`independent_pre_run_review_passed=false`、`execution_successor_present=false`、
`two_block_pilot_execution_ready=false`，formal/result/claim/security 继续为`false`。下一步仅为独立
pre-run R4 re-review；不得创建 execution successor 或调用 worker/solver。

### 2026-08-30 two-block pilot v2 pre-run re-review ESCALATE

上节“等待独立 re-review”现已由实际审查结论取代：独立`sol_reviewer`对 v2 给出
`ESCALATE`，原因是一轮聚焦返工上限已用尽但仍有 5 项未闭合。machine-readable receipt 为
`configs/rq2_public_grid_two_block_pilot_pre_run_review_escalation_v2.yaml`，SHA-256 为
`4a683712730fc37dc19d757db83ed660efcf2652bf7b66808783f635c3cfd88b`；它精确绑定 v2 inner
`fd7e0d92e78c92991602fe1dcd25c0a20e00fd6bc8f4f927a3431dda816b2598`和 outer
`fb2185a707e905480d6d0fc03b95c178420293807b309459548f99a31f782743`，且不授予任何执行权限。

审查已通过项仅表示对应 implementation evidence 成立：semantic-v1 registered raw-status mapping
及其 fail-closed 行为通过；sealed v1/v2 hash、canonical validate-only 的 0 solver/0 result write/
0 formal write、三个 v2 roots 不存在及相关进程为 0 均复核通过。这些通过项不能抵消以下 reviewer
findings：

1. `_worker()`在校验前对`request_path.resolve()`，CLI symlink/junction alias证据被抹去，测试未覆盖完整`_worker(--worker-request alias)`；
2. 任意父进程可调用公开`_build_controller_receipt/_build_request`自造内部一致证据，现有 forged test仅篡改既有nonce，未证明不可绕过；
3. v2 runtime import v1并委托`_formal_snapshot()`，但未live-verify v1 outer/inner/imported runner bytes，review后v1 drift可被接受；
4. `_result_manifest()`忽略额外空目录且仅`is_symlink`、不拒绝junction/reparse，exact tree不成立；
5. publication对抗测试只调用`_validate_copied_worker_pair()`，未覆盖`_publish_result()`/manifest/final reread/extra member/rename boundary。

因此当前`independent_pre_run_review_passed=false`、`execution_successor_present=false`、
`two_block_pilot_execution_ready=false`、`two_block_pilot_executed=false`、
`post_result_review_passed=false`。pilot 未执行；`formal_execution_ready=false`、
`user_formal_run_authorized=false`、`formal_result_exists=false`、`claim=false`、
`security_certified=false`继续成立。v1/v2 candidate bytes 必须保持不变；不得创建 execution
successor，不得调用 worker/solver/pilot/formal/activation。后续只有用户另行决定并重新授权新的
versioned remediation/review 周期后才能继续。

### 2026-08-31 two-block pilot v3 remediation candidate（closed）

用户已重新授权一个新的 versioned remediation/review 周期，并以原文“授权给你，修复好之后就开始正式实验吧”
给出后续 formal run 的条件性授权。该原文已写入独立 machine receipt；它只有在 v3 独立 pre-run review、
独立 execution successor、完整 two-block pilot、具名 outage comparison、post-result 独立 review 与 formal
activation 全部闭环后才可能生效。当前`user_formal_run_authorized=false`，该 receipt 不是 activation，
也不授权当前 candidate、pilot、worker、solver 或 formal run。

v3 是全新的 sealed-candidate 拓扑，不修改 v1/v2 任一字节，并针对 v2 ESCALATE 的五项 finding 建立以下闭门证据：

1. worker 不再接受 request-file CLI；controller/worker 使用双向匿名管道、Popen 后实际 child PID/create-time、
   一次性 envelope 与 ACK。Windows 使用 explicit `handle_list`，POSIX 使用`pass_fds`；没有 file/env token
   fallback。其安全边界仅为拒绝 file-level bypass，不声称抵御同权限 process injection/handle duplication、
   administrator 或 kernel，故`security_certified=false`。
2. 任一路径均在 resolve 前逐 segment 使用`lstat`检查 POSIX symlink 与 Windows junction/reparse；旧
   `--worker-request` CLI 在任何路径处理前被 parser 拒绝。controller 与 worker 每个入口都 live-verify
   v1 outer/inner/6 live members、v2 outer/inner/6 live members、v2 ESCALATE、recovery-v2、semantic-v1
   与 v3 chain；v3 不 import v1/v2 pilot runtime。
3. result manifest 是 typed exact tree，显式记录 directories 与 files；额外空目录、extra member、nested
   manifest、symlink/junction/reparse 与 type swap 均 fail closed。真实`_publish_result()`负责 source/memory
   hash、copy、完整 payload/certificate 与 0008 comparison、typed manifest、最终 authority/tree/payload
   重读，并在所有门通过后才 atomic rename；final-boundary tamper 必须保持 target absent。
4. focused v3 tests 当前为`23 passed`。其中真实 OS synthetic capability probe 只启动极小 Python 子进程，
   验证 explicit handle inheritance、post-Popen identity binding、single frame/ACK；ordinary file、wrong
   direction 与 replay 均被拒绝。probe 将 scientific loader、solver、result/formal write 设为硬失败并保持为 0。

当前状态仍是`remediation_candidate_v3_execution_closed`：`independent_pre_run_review_passed=false`、
`execution_successor_present=false`、`two_block_pilot_execution_ready=false`、`two_block_pilot_executed=false`、
`post_result_review_passed=false`、`formal_execution_ready=false`、`formal_result_exists=false`、`claim=false`、
`security_certified=false`。pilot 尚未执行；下一步只允许完成 0-solver 验证并提交独立 R4 pre-run review。

封存验证已完成：v3 authorization/config/runner/validator/tests/inner/outer SHA-256 依次为
`f696e76a1fedba8335af62e8914b12bb9385606525cf8170d0b11ffdb3900e52`、
`fd6f0c01a425c6a431a4ac384d723a1c61f5516f0056a4d17e451ff1ed490e01`、
`4248eaf3e25293ad20fafd67c09ec9e5293bb15a23618a91ec49c764d4710f6b`、
`7c578276f6e3483223ca1830b3c6e8135f6464ff906e140cecc8e7e56d2bccb8`、
`3ba21a9933b4bd82bc6e8192103c17a2faaf30741031a534f3a60289efea04f1`、
`9c3e0318daa06d7cac830c3e65f7bc9950b26c63f775cdabbe7d0315a9dad1d0`和
`d08b3049e43837397b1459edc9f4ecfa8d7e20419bcbbbf73f68d109f3dd10f9`。focused v3
为`23 passed`，相关 v1/v2 pilot + recovery v1/v2 + diagnostic 回归为`91 passed`，Ruff 通过。
canonical validator 返回`validation_passed=true`、`execution_ready=false`、0 worker process、0 solver、
0 result write、0 formal write；v3 三个 roots 与 recovery/formal output roots 均不存在，相关进程为 0，
formal runner/config hash 与 9 个 checkpoint 均未改变。该验证只形成等待 independent review 的 closed
candidate 证据，不形成 pre-run `PASS`。

### 2026-08-31 two-block pilot v3 REWORK 与 v4 focused remediation（closed candidate）

独立 pre-run reviewer 对 v3 给出本周期首次`REWORK`。versioned receipt
`configs/rq2_public_grid_two_block_pilot_pre_run_review_rework_v3.yaml`（SHA-256
`af9a2b52b9bd3597804d523a5a16d0cec607f6616c40aa8b8b1a3e0373448ba3`）精确绑定 v3 inner/outer，
并保持`no_execution_authority=true`。v1/v2/v3、既有 manifests/receipts、formal runner/config、9 个
checkpoints 与 results 均未修改。

新的 v4 只作为`rework_candidate_v4_execution_closed`封存：production consumer 必须先发送 HELLO，随后只接收
一个 capability frame，并在 ACK 与 scientific data load 前以同一 watchdog 验证 bounded EOF；尾随字节或第二
frame 均 fail closed。controller 以`execution_index=1,2`和 immutable accepted-evidence ledger 固定
`0008→0009`，第二项绑定第一项的 accepted-evidence/payload/attempt-receipt/ACK digest。child stdout/stderr
仅写 exclusive ordinary files；HELLO/frame/EOF/ACK/completion 共用 21600 s watchdog、5 s resource sampling、
8 GiB private-commit 与 2 GiB system-commit reserve，异常路径执行 terminate→bounded wait→kill→bounded wait。
timeout、resource stop、nonzero、unresolved 或证书失败只表示 honest incomplete，不推断 infeasibility。

worker attempt receipt、controller validation receipt 与 post-rename publication seal 已分离；只有 atomic rename
及完整 readback 后的独立 success seal 可写`published=true`。publication 在 copy 后和 rename 前均以 controller
内存中的 frozen accepted-evidence（exact ACK bytes/hash、PID/create-time、source bytes、scientific canonical
hash、nonce/envelope）重验；typed manifest 记录 exact dirs+files 并拒绝 empty extra dir、nested manifest、
file/dir swap、symlink/junction/reparse、co-tamper 与 target preexist。所有 v4 authority 路径均在 resolve 前
逐 segment 检查 alias/reparse；future execution 还必须由外部 trust root 提供经 review 的 v4 outer digest，
当前该值为`null`，禁止 dynamic self-acceptance。

验证结果：focused v4 为`55 passed`；v1/v2/v3 pilot、recovery v1/v2 与 diagnostic 相关回归为`114 passed`；
Ruff 通过。canonical validate-only 返回`validation_passed=true`、`execution_ready=false`、0 worker process、
0 scientific loader、0 solver、0 result write、0 formal write。REWORK receipt/config/runner/validator/tests/inner/outer
SHA-256 依次为`af9a2b52b9bd3597804d523a5a16d0cec607f6616c40aa8b8b1a3e0373448ba3`、
`d71069e242ba90f6ce8c7af8a77fd470f4e45c794c849f04786faf763baa0fe1`、
`3b6e55605f56cee1e871d72b15ddfec0963ce727ec863a08f4cbac441d7541e9`、
`3218aac00a87ad6eb5dcd6a8c19f3782b9bf6c5b10e37a58a4d65f27e527e2f2`、
`3d4e6227eb78ca435c0e613f94e8df6b85ea1cd038dd1a95cb8c5b8044a9413a`、
`1f03580ef26467c069206a1144e8f6f575f03cb44565c7c82fe82360f128dfdb`和
`a4fa236bec8e6009bee75772e012fcccd09372068287674725c4d5a4fe8afd7b`。

当前`independent_pre_run_review_passed=false`、`execution_successor_present=false`、
`two_block_pilot_execution_ready=false`、`two_block_pilot_executed=false`、
`post_result_review_passed=false`、`formal_execution_ready=false`、`user_formal_run_authorized=false`、
`formal_result_exists=false`、`claim=false`、`security_certified=false`。本轮没有启动 production worker、solver、
pilot、formal 或 activation。下一步只能提交 v4 给独立 R4 pre-run review；未取得新的 machine PASS receipt 前
不得创建 execution successor 或执行 pilot。

### 2026-08-31 two-block pilot v4 ESCALATE 与 v5 post-rename commit remediation（closed candidate）

独立 reviewer 对 sealed v4 的复核结论为`ESCALATE`：v4 在 result directory 已 atomic rename、旧式
`published=true` success JSON 已落盘后，若 publisher 抛出异常，调用方仍会收到 failure，因而同一 attempt
可同时出现 published-success 与 reported-failure。该事实已由真实 v4`_publish_result()`的 synthetic
post-commit seam 复现；versioned receipt
`configs/rq2_public_grid_two_block_pilot_pre_run_review_escalation_v4.yaml`（SHA-256
`9288bc637f7ad9d7f4876e8dce2846597e56f288324b825d0cb9330dc007bcc9`）精确绑定 v4 inner
`1f03580ef26467c069206a1144e8f6f575f03cb44565c7c82fe82360f128dfdb`与 outer
`a4fa236bec8e6009bee75772e012fcccd09372068287674725c4d5a4fe8afd7b`，并明确不授予 execution authority。

新的 v5 只修复 post-rename commit 状态机；v4 science、transport、ledger、certificate/comparison 与
publication pre-commit 实现继续由 sealed v4`_publish_result()`提供且 source SHA-256 固定为
`e014b73c608e2bce7ee59a486a718ec54149b66c7f9308b424b907155ae3d791`。v5 显式复用 repair-010：

1. 唯一不可撤销 commit point 是包含`success.json`与`SHA256SUMS.json`的 fresh immutable directory
   atomic rename；exact payload/manifest bytes 与 hashes 在 rename 前冻结。
2. publisher 异常后，target/seal 均不存在时只返回`honest_incomplete`；exact seal 与 result 的全部
   authority/tree/payload/comparison/evidence binding 重验通过时返回`committed_success`；存在但不可读、
   corrupt、mismatch 或与 terminal state 共存时抛出`commit_indeterminate`，禁止 resume，且不得产生
   published-success 与 terminal/failure 双态。恢复入口只接受 exact committed seal，不依据文件外形推断成功。
3. 不删除、不覆盖无法证明的 target/seal；v5 没有 terminal writer。timeout、异常或 incomplete 继续不推断
   mathematical infeasibility。

验证结果：v5 focused 为`20 passed`；v1–v5 candidate related regressions 为`137 passed`；repair-010
三态规则的 12 个针对性测试为`12 passed`；Ruff 通过。repair-010 两个完整历史测试文件另有
`56 passed, 2 failed`，两项均由仓库中预先存在的冻结 calibration output/launcher root 触发，未清理或
改写这些历史 artifacts，不是 v5 状态机回归。canonical validator 返回`validation_passed=true`、
`execution_ready=false`、0 worker、0 scientific loader、0 solver、0 result write、0 formal write；v5 roots
不存在，formal runner、activated config 与 9 个 checkpoints 未改变。

v5 config/runner/validator/tests/inner/outer SHA-256 分别为
`5360b4461af277c59abad78454014d22af1d11394990af07f291cc6b7695f2c6`、
`41cdb2efab3ec96386be00c88f18ee5fa42233ddd3a88c78c81b3cc981bc9d48`、
`605698b976b892dfb64002a1c44c5979cc45106a86cb05ec7958a7c3d955add6`、
`aca63aa0a2c901d6e0ed388b852321e5d1c9e8018b1d274cbc8e5a9f22a07316`、
`0d81d1ebe376969bac02d17aec9f4afa4bd077a9c71cdd906ae0538cb0793818`和
`1be9ddd051da3ae71f7529fadf02745d5e3e58ee84649d0b557e0f14e9e65fac`。

v5 当前仅为`postcommit_remediation_candidate_v5_execution_closed`；external reviewed outer 为`null`，
`independent_pre_run_review_passed=false`、`execution_successor_present=false`、
`two_block_pilot_execution_ready=false`、`two_block_pilot_executed=false`、
`post_result_review_passed=false`、`formal_execution_ready=false`、`user_formal_run_authorized=false`、
`formal_result_exists=false`、`claim=false`、`security_certified=false`。用户持续授权只在 pilot、独立 reviews、
versioned successor 与 formal activation 全部闭环后生效；当前下一步仅为独立 R4 pre-run review，不得启动
production worker、solver、pilot、formal 或 activation。

### 2026-08-31 two-block pilot v5 REWORK 与 v6 presence-safe recovery（closed candidate）

独立 reviewer 将 sealed v5 判为`REWORK`。真实 Windows junction 复现显示：success commit 目录改为 junction
并删除 backing 后，`os.path.lexists(success)=true`，但 v5 的`Path.exists()`返回 false，继而错误分类为
`honest_incomplete`并在 outcome 中写`success_commit_exists=false`。versioned REWORK receipt
`configs/rq2_public_grid_two_block_pilot_pre_run_review_rework_v5.yaml`（SHA-256
`aa0e342be0a1938d69aaa1d02994d16fe19e343355490c3c551d2e34026dff7d`）绑定 v5 inner
`0d81d1ebe376969bac02d17aec9f4afa4bd077a9c71cdd906ae0538cb0793818`与 outer
`1be9ddd051da3ae71f7529fadf02745d5e3e58ee84649d0b557e0f14e9e65fac`，且不授予执行权限。

v6 仅修复 presence/path recovery gate；sealed v4 pre-commit/science/transport/ledger 与 sealed v5 exact-commit
语义均按 source hashes 绑定且未修改：

1. reconciliation、recovery 与 outcome 对 result/success/terminal 的 lexical path 逐级执行
   `os.path.lexists→lstat`，检查 POSIX symlink、Windows junction/reparse、非 anchor mount、不可访问或
   非目录祖先；在这些检查前不调用`resolve()`。
2. 只有 success 与 terminal 全链`clean_absent`才是`honest_incomplete`；任何 terminal ordinary
   file/directory 或 link/reparse/mount/ancestor appearance 均为`commit_indeterminate`；只有 exact ordinary
   success directory 且 terminal 全链 clean absent 才是`committed_success`。
3. outcome 的 legacy`*_exists`字段统一表示 lexical path appearance，并附完整逐级 presence audit；broken
   link/junction 不再报告不存在。任何 indeterminate 状态均不删除或覆盖路径、不创建 terminal、不允许 resume，
   也不推断 mathematical infeasibility。

验证结果：v6 focused`20 passed`，其中 Windows native post-commit broken-junction E2E 单独复跑
`1 passed`；v1–v6 related regressions`157 passed`；Ruff 通过。canonical validator 返回
`validation_passed=true`、`execution_ready=false`、0 worker、0 scientific loader、0 solver、0 result write、
0 formal write；五个 v6 roots 均为逐级审计后的 clean absent。v1–v5 sealed hashes、formal runner、activated
config 与 9 个 checkpoints 未改变，formal/recovery output roots 仍不存在。

v6 config/runner/validator/tests/inner/outer SHA-256 分别为
`a085ce907b39d57087c452c002349cc39be4c41d9c2865a5763ff73a89348b07`、
`21c315f046b3bf62f1c8b16eb834e9bf172dfeb8f361fae17a7d2433e49151fa`、
`c9bdfb5e4113d8d5a5b1206339db67ab57a42fe48abb4f218a71a6e63e87fda4`、
`e0c1b0d3ebcb2a48b48e58f7c65cd5d1f08f61a9dd7b6c3b1b5a0d7c279b9cf4`、
`990a9f5bec908a32d41b5d0c7fdecba064cb8e8df6b129295ef2489a82e468a9`和
`ab9bfb5d89a383a6b68ee8630c9ca14df819bd9f885899e2fd07f76f136dfb20`。

当前仅为`presence_recovery_candidate_v6_execution_closed`；external reviewed outer 为`null`，全部
independent-review/execution-successor/pilot/post-result/formal/result/claim/security gates 为`false`，
`user_formal_run_authorized=false`。本轮未运行 production worker、solver、pilot、formal 或 activation；
下一步只允许 independent R4 pre-run review。

### 2026-08-31 two-block pilot v6 ESCALATE 与 v7 immutable publication snapshot（closed candidate）

独立 reviewer 对 sealed v6 给出`ESCALATE`。v6 在 reconciliation、outcome、committed-result validation、
recovery 和 final acceptance 中分别重探 result/success/terminal，因而同一决定可能混用不同 path-state
观测；此外 success clean-absent 分支没有约束 result 必须 clean absent 或为明确允许的 ordinary unsealed
result directory。machine-readable receipt
`configs/rq2_public_grid_two_block_pilot_pre_run_review_escalation_v6.yaml`（SHA-256
`c26afa1ddf77c98e5048609bc6cf17e30231e6417c8208069acce42a803754bd`）精确绑定 v6 inner
`990a9f5bec908a32d41b5d0c7fdecba064cb8e8df6b129295ef2489a82e468a9`与 outer
`ab9bfb5d89a383a6b68ee8630c9ca14df819bd9f885899e2fd07f76f136dfb20`，并明确
`no_execution_authority=true`。

v7 仅修复 publication presence/recovery gate；sealed v4 science/transport/ledger/pre-commit 与 v5/v6
post-commit scientific bindings保持不变。每个 reconciliation/recovery/validator 决定在任何 classification
branch 或 resolve 前构造一个深度不可变的`PublicationPresenceSnapshot`，一次性记录 canonical lexical
result/success/terminal 及每级 ancestor 的`lexists`、`lstat`、reparse、mount 和 accessibility。outcome 不再
重探路径。只有三条 leaf clean absent 且 ancestors ordinary，或 ordinary unsealed result directory 加
clean-absent success/terminal，才是`honest_incomplete`；任何 file、alias、junction/reparse、mount、
inaccessible/nonordinary、terminal appearance、corrupt/mismatch 或 dual state 都是
`commit_indeterminate`。仅 exact complete result、exact bound success 和 clean-absent terminal 可形成
`committed_success`；接受前另取且仅取一次 final snapshot，并在该 snapshot 下全量重验 result tree、
manifest、payload、certificate-derived bindings 与 success bytes/hashes。snapshot 是一次逻辑一致观测，
不声称抵御同权限恶意进程在连续 OS metadata calls 之间的竞争。

验证结果：v7 focused`40 passed`，v1–v7 related`197 passed`，Ruff 通过；canonical validator 与 runner
`--validate-only`均返回`validation_passed=true`、`execution_ready=false`、0 worker、0 scientific loader、
0 solver、0 result write、0 formal write。Windows native junction、POSIX/reparse、mount、inaccessible、
unreadable、corrupt/manifest/binding mismatch、all-absent、ordinary-unsealed、exact-success 和
success+terminal truth-table 均覆盖 production post-commit 与 recovery entry。v7 config/runner/validator/
tests/inner/outer SHA-256 分别为
`9a5f1f342e4c4982b1b7bcdf13e71ed204cb2319fc2c29b5a49a7d4fdab8da17`、
`165b3ef4b1ef4f894b2d1740948ee92033776d547d90b74e02855820227ab105`、
`d84a9ba2919ff8ed59aa42c67e3f6f2f8a58c064007e9d755405217735cb0c92`、
`052a2d11757656398538a0ab705a9abebf7fed165edb557b869d6f8adaced99d`、
`06ad8f34bbe5e9f52755431506e495a670e740092636305b8c12f1f495c6a976`和
`101c0c1399505c9ddf9f1613afc3981139aedf85645a6e8797cc86d217faed35`。

当前仅为`publication_presence_snapshot_candidate_v7_execution_closed`；external reviewed outer 为`null`，
independent-review/execution-successor/pilot/post-result/formal/result/claim/security gates 均为`false`，
`user_formal_run_authorized=false`。本轮未启动 production worker、solver、pilot、formal 或 activation；
下一步仅提交 independent R4 pre-run review，不能把 closed candidate 或测试结果解释为执行授权。

### 2026-08-31 v7 independent PASS 与 execution-successor v1（closed）

独立`sol_reviewer`对 v7 最终封存给出`PASS`，Blocker/Major/Minor findings 均为空。machine receipt
`configs/rq2_public_grid_two_block_pilot_pre_run_review_pass_v7.json`（SHA-256
`a98298f270e57b699808dad0e5b97cd9475a688e6d9ca7b263428ca95aa233a4`）精确绑定 v7 七项 live hashes。
该 PASS 仅关闭 v7 implementation/pre-run review 门，并授权构建、零 solver 验证新的 versioned execution
successor；它不授权 pilot、formal、activation、result、claim 或 security。

execution-successor v1 是独立的 standard-library-only bootstrap，不 import v7 runner、project loader、worker
或 solver，也不复制或改变 science/transport/ledger/postcommit/frozen-formal 语义。它在任何 project module
import 前验证 exact v7 outer、PASS receipt、用户授权 receipt 的条件性范围、successor 自身 inner/outer、锁定
解释器路径与 SHA-256、exact direct-script argv/cwd/host、精确环境 allowlist、fresh process、related-process
inventory、五个 pilot roots 与三个 protected formal/recovery roots clean absent，以及 8 GiB child cap 加 2 GiB
host reserve 的 available-virtual-memory 门。唯一 CLI 是`--validate-only`；任何 execution 路径均不存在。

successor config/bootstrap/tests/inner/outer SHA-256 分别为
`9761ba5f2d384c22ed7f79b8d32aedf9f1a8292c94ded77b262273978f4e1836`、
`38dfb0a5608a98f1709ac9d25f77db1a3bb22334599af21ef8b06856ae70408d`、
`766326b728295999b90a3ecb6d2323427b3b06e101326c8ff2d457710c23ca04`、
`15a86b1fc2aad3112dedc71af17ff857b02236c5d75b05e347398c9e3ab851b2`和
`c89b8baaa5ec1b52595aa6297d53dc0780a380b59a96455032f8b449a95329a7`。focused tests 为
`20 passed`，v1–v7 candidate 加 successor related regressions 为`217 passed`，Ruff 通过；锁定解释器在清空后按 allowlist 重建的环境中 direct-script validate-only 返回
`validation_passed=true`、`status=READY_FOR_INDEPENDENT_REVIEW`、`execution_ready=false`，且 0 project
import、0 worker、0 loader、0 solver、0 result write、0 formal write。

当前 successor 状态为`execution_successor_candidate_closed`：independent successor review receipt 与
activation wrapper 均为`null`，所有 successor-execution/pilot/formal/result/claim/security gates 为`false`，
`user_formal_run_authorized=false`。未来只能由外部独立 review receipt 精确绑定本 outer，再由新的不可变
activation wrapper 闭环；successor 不得动态接受或自签自身执行权限。当前结论仅为
`READY_FOR_INDEPENDENT_REVIEW`，不得启动 production worker、solver、pilot、formal 或 activation。

### 2026-08-31 execution-successor v1 REWORK 与 v2（closed）

独立 reviewer 对 execution-successor v1 给出本周期唯一一次`REWORK`：无 Blocker，三项 Major 分别为
Toolhelp enumeration 未区分真实 EOF 与 API error、formal checkpoint inventory 未证明 exact lexical nine
ordinary files、以及 absent-root/locked-Python path gate 对 OS error 与逐段 lstat 证据不够严格。machine
receipt `configs/rq2_public_grid_two_block_pilot_execution_successor_review_rework_v1.json`（SHA-256
`a238cc81845cdecc6a09812932889a19d8dddd7b991b4f3bb17d023ec74183f4`）绑定 v1 outer
`c89b8baaa5ec1b52595aa6297d53dc0780a380b59a96455032f8b449a95329a7`和完整 findings，且明确
`no_execution_authority=true`。v1 全部 sealed bytes 未修改。

versioned successor v2 仅修复上述启动前 fail-closed 边界：`Process32FirstW`失败一律拒绝；
`Process32NextW`仅`ERROR_NO_MORE_FILES=18`为正常 EOF，其他 error 拒绝，inventory 必须包含当前 PID。
checkpoint directory 使用`scandir + entry.stat(follow_symlinks=false) + strict lstat`审计 exact 9 个 ordinary
files，并拒绝 extra directory、alias/junction/reparse、special、unreadable、type swap 或 enumeration error。
八个 absent roots 每级使用 lstat 区分 file/path-not-found 与 permission/other error，不使用`lexists`吞并异常。
locked Python executable 及所有 ancestors 在 hash 前通过同一个 strict lstat/reparse/mount/accessibility/type
gate。bootstrap 仍为 standard-library-only，project preimport fail closed，且唯一 CLI 为`--validate-only`。

v2 REWORK receipt/config/bootstrap/tests/inner/outer SHA-256 依次为
`a238cc81845cdecc6a09812932889a19d8dddd7b991b4f3bb17d023ec74183f4`、
`4b88cdccabdb731607b7064ac60a73994b8c9df0948a99b4462f1594c7277245`、
`97b092ec84f97dc2334b9c8fddc5df037f6a7efc3502701b7f6fb540cd1dad80`、
`6e494152dfdb5721d4ec877ea630cabea73f61d5768dd8835fccbb55676dd312`、
`9cf0e626beb00e6fe6fa06acb600fe8406b04bc99bdc1327ec8089610b919bf9`和
`5b9cdb826f6ae44c1e134574d7b9563e4353dd9bd28c3eebd32e487e57d2a311`。focused 为`58 passed`，
v1–v7 candidates 加 successor v1/v2 related 为`275 passed`，
canonical 清空环境 direct-script validate-only 返回`validation_passed=true`、
`status=READY_FOR_INDEPENDENT_REVIEW`、`execution_ready=false`及 0 project import/worker/loader/solver/
result/formal write；同环境无`--validate-only`调用 exit 1 并 fail closed。

v2 当前仍为`execution_successor_v2_candidate_closed`；independent review、activation、pilot、formal、result、
claim、security gates 全部关闭，`user_formal_run_authorized=false`。scientific/transport/ledger/postcommit 与
frozen formal semantics 未变；不得启动 production worker、solver、pilot、formal 或 activation。

### 2026-08-31 execution-successor v2 PASS 与 nonformal activation candidate v1（closed）

独立`sol_reviewer`对 successor v2 的最终复审为`PASS`，无 Blocker/Major/Minor。versioned machine receipt
`configs/rq2_public_grid_two_block_pilot_execution_successor_review_pass_v2.json`（SHA-256
`ad692bfdfec2b90cda49dfc54dc08fd1383bf9e2a4524775676f0f31025ce855`）精确绑定 v2 outer
`5b9cdb826f6ae44c1e134574d7b9563e4353dd9bd28c3eebd32e487e57d2a311`及全部六项 review evidence。该
PASS 只关闭 successor implementation review 并授权建立 0-solver activation candidate；它不直接授权
worker、pilot、solver、formal 或 activation。

新的 activation candidate v1 是 standard-library-only、validate-only-first 的独立封口层。冻结的未来非正式
pilot 合同严格为`holdout_s20260822_0008`后`holdout_s20260822_0009`，每 block 一个 fresh worker，禁止
resume/retry/reorder/skip；0009 必须绑定 controller 内存中已接受的 0008 evidence digest，PID 必须不同。
watchdog 为每 block 21600 s，child private commit cap 为 8 GiB，host reserve 为 2 GiB。未来调度仅引用
sealed `v7.v4._dispatch_one`/`v7.v4._worker_from_capability`与 v7 publication/recovery，activation 层不复制
scientific/transport/publication semantics。timeout、resource stop、nonzero exit、missing incumbent 与 unresolved
只映射为`honest_incomplete`；publication race 为`commit_indeterminate`；均不构成 infeasibility evidence。

candidate 本身永久不能自签执行许可：当前 future review receipt path/hash、reviewed outer 与 future wrapper
path/hash 全为`null`。未来独立 activation-review PASS 必须精确绑定 activation outer、successor-v1/v2、v7
PASS、用户条件授权及整条 live chain；再由新的 immutable execution wrapper 固定 receipt path/hash 并做
double-read/race 检查。CLI 提供的 receipt/path/hash 不能形成 authority。当前`--execute`在任何 project import
前因 wrapper binding 缺失而 fail closed；formal/Gurobi/recovery activation entrypoints 均不可达。

PASS receipt/config/bootstrap/tests/inner/outer SHA-256 依次为
`ad692bfdfec2b90cda49dfc54dc08fd1383bf9e2a4524775676f0f31025ce855`、
`e18c3a1d4b6197068b96e93338eb48e8bca0b06535b51007c7340b2ba783c8a6`、
`c7928b06f7307c3eda001e5135dcbaae9696cd83bc44e3ff4c17e78b077a1590`、
`2cdd50071facf890c322df5bdc421cc013cc85c179ca806034d128ff91d959e9`、
`7aef813591a753567281b0119620437fe1c04f444c1d04f743c44ef25a09d289`和
`844f4a59527306962e97e7879e4ccb7abb1893b65a819b782c56110e4df073f2`。focused 为`29 passed`，
Ruff 通过；canonical sanitized-env direct-script validate-only 为`validation_passed=true`、
`activation_review_present=false`、`execution_ready=false`及 0 project import/worker/loader/solver/result/formal
write；forged`--execute`为 exit 1。v1–v7 candidates、successor v1/v2 与 activation candidate related
回归为`304 passed`。

当前状态为`nonformal_two_block_pilot_activation_candidate_closed`；activation independent review、execution、
pilot executed、formal/result/claim/security gates 全为`false`，`user_formal_run_authorized=false`。本轮未运行
production worker、loader、solver、pilot、formal 或 activation；下一步仅为独立 R4 activation-candidate review。

### 2026-08-31 activation-v1 REWORK 与 activation/transport successor v2（closed）

activation candidate v1 独立审查为本周期唯一一次`REWORK`：Blocker 是其所指 v4 `_dispatch_one`/
`_worker_from_capability`永久 closed，且 frozen argv/authority 不能与未来 wrapper 自洽；两项 Major 是 v1
ledger 只校验新 record、可由伪造历史解锁 0009，以及 future review receipt 过早要求 execution flags 为 true。
machine receipt `configs/rq2_public_grid_two_block_pilot_activation_review_rework_v1.json`（SHA-256
`47977a68a61d4bdc1aa6281523dd6ecfd6d3a596a6a3184680ec8eb713c4464b`）精确绑定 v1 outer
`844f4a59527306962e97e7879e4ccb7abb1893b65a819b782c56110e4df073f2`和全部 findings，并明确不授予执行权限。
v1 全部 sealed bytes 未修改。

versioned v2 新建自己的 standard-library controller/worker transport；不调用、重开、monkeypatch 或绕过 v4
closed entrypoints。worker exact command 为新 v2 module 的 hidden pre-loader probe 入口，controller 使用真实
anonymous pipes（Windows explicit `handle_list`，POSIX `pass_fds`）完成 HELLO、one-shot capability、bounded
EOF、ACK 与 canonical source/attempt-receipt bytes。当前唯一可运行路径在 loader/solver/publication 前截断；
production worker/dispatch 不存在。未来只允许在独立 reviewed wrapper 和另一份 dispatch authorization receipt
闭环后复用 sealed v4 scientific/certificate primitives 与 v7 publication/recovery primitives。

v2 使用 frozen `AcceptedEvidence`与 fresh in-memory `ControllerLedger`。production evidence 在进入 ledger 前还必须
绑定由当前 controller 对 exact live `subprocess.Popen`创建的一次性`AttemptCapability`；token 同时绑定 session、
block/index、nonce、PID 与 create-time，缺失、伪造、身份漂移或重放均 fail closed。pre-loader probe 只证明真实
anonymous-pipe/ACK/source-byte transport，明确不进入 production ledger。ledger 不接受 constructor history，
每次 records/read/predecessor/append 都从 genesis 重验 exact dataclass/schema/type、canonical envelope/ACK/source
bytes 与 hashes、block/index/order、predecessor 和 ledger digest、PID+create-time、nonce、request/envelope、ACK、
source/receipt identities，并要求当前 controller session HMAC；伪造、截断、跨 session、变异、replay、reorder、
block swap 与 PID/nonce 复用均 fail closed。0009 只可由同一 fresh controller 内存中已验证并接受的 0008
digest 解锁；no resume/retry/reorder/skip 不变。

future activation review 的唯一正向 effect 是授权创建和独立审查新的 immutable execution wrapper；
`activation_execution_authorized=false`与`two_block_pilot_execution_authorized=false`保持冻结。wrapper 自身取得
独立 PASS 后，仍须另一份 exact dispatch receipt 与人工 review 才能讨论 dispatch。timeout/resource stop/
nonzero/missing incumbent/unresolved 仍为`honest_incomplete`，publication race 为`commit_indeterminate`，均不
推断 infeasibility；formal/Gurobi/recovery activation entrypoints 不可达。

REWORK receipt/config/runner/bootstrap/tests/inner/outer SHA-256 依次为
`47977a68a61d4bdc1aa6281523dd6ecfd6d3a596a6a3184680ec8eb713c4464b`、
`b63dd42ac4666066af298e38ea0ab289cc12302ca266c044ac39f5e6a8935535`、
`81fbe723939f890088842d1f03a5d8cf6c8a3abe39457ef9ad169e4752db69e8`、
`f37c1e205e2c1deb40a87d793486f4c82961eae146a8420b87e549cf26cc67de`、
`953bee9808f068c261979c2eed96ff6f8613ec30d3b5fa6e063a16be5a8e9a6b`、
`8a4553bbf23cfde50b812877fd7ccaaa3d4cc73277a73f674d3d61efd97e65ef`和
`24a1d75d43e7d1db8c59449781b947fdfb370e6658e8a5985e6b97656b96ed6a`。focused`27 passed`，
v1–v7 candidates、successor v1/v2、activation v1/v2 related`331 passed`，Ruff 通过。真实 Windows probe
成功启动并回收 fresh child，验证 ACK/source bytes，且 loader/solver/result/formal write 全为 0。canonical
sanitized-env validate-only 返回`validation_passed=true`、`execution_ready=false`、review/wrapper/dispatch absent、
production dispatch false 及全零执行计数；canonical`--execute`在 wrapper/dispatch authority absent 处 exit 1。

当前仅为`activation_transport_v2_candidate_closed`；activation-v2 review、wrapper、wrapper review、dispatch
authorization、pilot、formal/result/claim/security gates 全为`false`，`user_formal_run_authorized=false`。本轮未
启动真实 loader、solver、pilot、formal 或 activation；下一步仅提交独立 R4 review。同一 finding 再失败须
`ESCALATE`。

### 2026-08-31 activation-v2 ESCALATE 与 controller-owned transport v3（closed）

activation-v2 独立复审因同一 origin-assurance finding 正式`ESCALATE`：公开
`begin_transport_attempt(process, ...)`与`accept_verified_transport(evidence, capability)`仍允许 caller 提交
arbitrary live Popen 以及自造 ACK/source/evidence；focused tests 也直接注入 capability，故只能证明内部一致，
不能证明 evidence 来自 sealed production-worker command 与匿名管道。machine receipt
`configs/rq2_public_grid_two_block_pilot_activation_transport_review_escalate_v2.json`（SHA-256
`17317027847ad7b9af9d6ce9e8fd9650e0508cad23930ee36be4a83d465b9586`）精确绑定 v2 outer
`24a1d75d43e7d1db8c59449781b947fdfb370e6658e8a5985e6b97656b96ed6a`；v1/v2 sealed bytes 未修改。

versioned v3 重新建立 controller-owned 不可分割状态机。caller 无 Popen/capability/ACK/source/evidence accept
API；`ControllerSession`唯一创建 exact locked Python worker command、cwd、sanitized environment 和 Windows
`handle_list`/POSIX`pass_fds`，读取 HELLO 后绑定 actual PID/create-time/PPID/module/config hashes，写入唯一
envelope并验证 bounded EOF、ACK、canonical source/scientific payload/certificate inventory bytes，只有完整
`ACCEPTED_COMPLETE`结果才在同一内部路径构造 HMAC record 并 append。attempt index 在 spawn 前永久消费，失败
不回滚；`single-active-attempt`、no retry/resume/reorder/skip 均 fail closed。0009 只在同一 session 的0008
internal accepted record 完整从 genesis 重验后开放。

真实 review-only E2E 使用同一个 hidden`--internal-production-worker`与 OS anonymous pipes；worker完成全部
authority/HELLO/frame/EOF校验后在 scientific import/data loader 前返回
`NON_ACCEPTED_PRELOADER_BOUNDARY`，`accepted=false`、`unlock_successor=false`、records 为空且
loader/solver/result/formal write 均为 0，因此不能解锁0009。未来 production branch 仅在独立 activation review、
immutable wrapper review、另一份 exact dispatch receipt 与 user-authorization hash 全链闭环后，hash 校验 sealed
v4/v7 authority并调用`candidate_v4._stage_context/_load_worker_data`、
`recovery.v4._process_block`和`recovery._validate_scientific_payload`；不调用 v4 gated dispatch/worker/run，也不复制
科学模型或阈值。威胁声明只覆盖 code/OS-pipe origin assurance，不声称抵御同权限恶意父进程内存篡改、管理员或
kernel 攻击，`security_certified=false`。

ESCALATE receipt/config/controller/worker/bootstrap/tests/inner/outer SHA-256 依次为
`17317027847ad7b9af9d6ce9e8fd9650e0508cad23930ee36be4a83d465b9586`、
`3783d080f4dc7e64b84d1d7ca84f86abaaa1511ea67943b643a0c9e781c23f44`、
`4a0eec0aa6d30ce2037bea855488973fd4436234c391c0952e100d66000c2b05`、
`8928425399806d2aa37cdac631815151eeaf0a9225e13c531bd82147159fd926`、
`3e127b55ef6ea32d23ad8869c32a74988877b39056ef3bd834b0e3678bc2c10e`、
`6070065ae31d8a4e1eebdf83e9b76cabf886c59d7d66d4c0adb5f1e95730deea`、
`7cc87f2f915ae2b1dbd3087d1312d6f633c28f030b48fd39627e9fe745fe89eb`和
`b7b5d85000091c052d257ee5ce4a6e280a6de52b6a813eaaad82d3473c92daee`。focused`28 passed`，
v1–v7 candidates、successor v1/v2、activation v1/v2/v3 related`359 passed`，Ruff 通过。canonical
sanitized-env validate-only 返回`validation_passed=true`、project import/worker/loader/solver/result/formal write
全 0、`execution_ready=false`；canonical`--execute`因 review/wrapper/dispatch authority absent 而 exit 1。

当前仅为`activation_transport_v3_candidate_closed`，等待独立 R4 review。activation review、wrapper、wrapper
review、dispatch authorization、pilot、formal/result/claim/security 均为`false`，
`user_formal_run_authorized=false`；本轮未运行 loader、solver、pilot、formal 或 activation。

### 2026-08-31 activation-transport v4 focused REWORK（closed candidate）

activation-v3 独立审查 verdict 为本周期唯一一次 `REWORK`。machine receipt SHA-256
`08b941a5730a1dea9140f0cf9392387943249d9b4e1369826aa0f1a8592442b1` 精确绑定 v3 outer
`b7b5d85000091c052d257ee5ce4a6e280a6de52b6a813eaaad82d3473c92daee`，不授予 execution authority。
v4 是新建且永久 closed 的 review candidate；v3 及其 sealed bytes 未修改。

v4 controller 的 `run_two_block_pilot` 与 `run_production_block`、以及 worker 的 production flag，均在读取
receipt/config、创建 pipe/Popen 或导入 scientific modules 前无条件拒绝。caller path、自洽 JSON、伪造三份 receipt
或 parent command 均不能把当前 candidate 打开。未来 executable route 必须新建 versioned controller/worker
successor，并硬绑定 exact v4 outer、独立 v4 PASS、wrapper review、dispatch receipt、controller/worker
module/path/hash、argv/cwd/sanitized environment/host；v4 本身不会生成该 wrapper，也不能原地 activation。

resource primitives 冻结为 child private commit cap 8 GiB、host commit reserve 2 GiB、preflight available commit
至少 10 GiB、默认 5 s sampling。sampling error、timeout、超限均只停止 exact controller-owned PID+creation-time，
返回 honest incomplete 且 `mathematical_infeasibility_inferred=false`。`RLock` 将 check、attempt consume 与 active
mark 放在 spawn 前同一临界区；真实 threads+Barrier 对抗只允许一次 review spawn，失败 attempt 仍永久消费。

scientific bridge 仅可由一次性 registered zero-solver seam 审计，不在 candidate execution path。审计 live-verify
recovery-v2 7-member manifest、candidate-v4 inner/outer、provenance contract 的全部 path/hash transitive members，
以及 `_stage_context/_load_worker_data/_process_block/_validate_scientific_payload` 的 exact signatures。zero-solver
seam 已覆盖 stage/load/process/validate 实际 counters、resolved、certificate mismatch、unresolved 与 exception；
solver/result/formal write 均为 0，任何失败都不推断 infeasibility。

封存 SHA-256：receipt/config/controller/worker/bootstrap/tests/inner/outer 依次为
`08b941a5730a1dea9140f0cf9392387943249d9b4e1369826aa0f1a8592442b1`、
`2392dadc238657948701b1129ccd7791ce6c97dea021b32808a7c5893222eddc`、
`04bfb1ac4deb51e1708c1eb668317b26e4cf2f3af68c35f18b96fb79f3af78a3`、
`0f7e6d8f09795baced787adc35d88843a5932a6056e0071ab7d6de9c919514e0`、
`43db037004e99125bc4d0e2577939b493d7927ce092d6a504b014e728235ec15`、
`8190eaf9ebf446750461ea89c6eba7214b3c7f477301c14e2fe94777bcbf5b01`、
`bf5e920d52173389d65d57493e46a24450ab2dc9060118986142ea9d307276ed`、
`9ba787c2d3b1ae3db64c675be2409a2a5d1cf2b2fe6b703133885c27efa5d16d`。focused
`25 passed`、v1–v7 candidates + successor v1/v2 + activation v1–v4 related `384 passed`、Ruff 通过；
canonical isolated validate-only 为全零 execution counters 且 `execution_ready=false`，canonical `--execute`
在 project import/dispatch 前拒绝。

当前 `activation_v4_independent_review_passed=false`；wrapper/wrapper-review/dispatch/pilot/formal/result/claim/
security gates 均为 false，`user_formal_run_authorized=false`。本轮只运行 non-accepting review-only preloader child，
未运行 production worker、loader、solver、pilot、formal 或 activation。下一步仅独立 R4 review。

### 2026-08-31 activation-transport v5 dual-resource remediation（closed candidate）

v4 independent review 已按正式 finding 转为 `ESCALATE`：v4 runtime monitor 只观测 child private commit、使用错误的
strict greater-than 判定，且没有在每个 5 s sample 同步守住 frozen recovery-v2 的 2 GiB system commit reserve。
ESCALATE receipt SHA-256
`af427494ccaade93428bf45f8409acb7ce33f50a7922e92ce14f326d42d0cd5f` 精确绑定 v4 outer
`9ba787c2d3b1ae3db64c675be2409a2a5d1cf2b2fe6b703133885c27efa5d16d`，不授予执行权限；v1–v4
sealed bytes 均未修改。

v5 仅修 resource monitor：每次同一 sample 获取 child private commit 与 system commit available；
`private >= 8 GiB`或`system_available <= 2 GiB`任一触达立即停止 exact PID+creation-time owned child。
preflight 仍要求 available commit `>=10 GiB`，但明确不能替代 runtime reserve monitor。sampling error、watchdog、
任一资源门触达均分类为 honest incomplete，`mathematical_infeasibility_inferred=false`；PID/creation-time 漂移为
ownership indeterminate，禁止误杀其他进程。

table-driven focused tests 覆盖 private `8 GiB-1/= /+1`、system available `2 GiB-1/= /+1`、双门组合、
sampling exception/malformed/negative、watchdog、foreign PID 与 creation-time drift。Windows native E2E 使用两个小型
sleep child：实际查询 target 的 PID/create-time/private/system sample，再以安全注入的边界 sample 精确终止 target；
bystander 在 target stop 后仍存活，随后仅按其自身 PID/create-time 回收，未申请大内存且未等待 5 s。

v4 已通过的 literal production hard-close、science dependency closure/registered zero-solver seam、`RLock`
atomic no-retry 均由 sealed predecessor 保持。future successor contract 强制后继同时继承 v5 dual-resource monitor、
v4 atomic no-retry、science closure 与 honest-incomplete semantics，并要求后继测试和独立 review 不得遗漏；当前 v5
production 仍在 pipe/Popen/import 前关闭，review-only 仍为 `NON_ACCEPTED_PRELOADER_BOUNDARY`且四类调用计数为 0。

封存 SHA-256：receipt/config/controller/worker/bootstrap/tests/inner/outer 依次为
`af427494ccaade93428bf45f8409acb7ce33f50a7922e92ce14f326d42d0cd5f`、
`8302af16df82369ed5c9656c49130eacca533a46ba5083d7d0f215a344103c27`、
`ff8868dea108e1d65886b916dc18a132c93f3532175d8a7cc8670c98fa25d5e0`、
`b46a934fee417971d548d1e229a0c1d2ddf6dff58a8c42310941ed1ad221b4c4`、
`7529431f3adc799e72132f676780f9106cacaa58f5103ac3ab7b813ea91df251`、
`d9adaebb8cca4410340f88aca420f7ea0cbc768ac6d1ab3e58481022ea7099dc`、
`1270a923241736c0b27da32d762f58ac1344a59ebca019a66d41cbf29912c4c5`、
`2afd26332d4965de625e46d8fdac3083559e5b6d8925876c00866ff368451e48`。focused
`23 passed`、v1–v7 candidates + successor v1/v2 + activation v1–v5 related `407 passed`、Ruff 通过；canonical
validate-only 全零且 `execution_ready=false`，negative execute 在 project import/dispatch 前 exit 1。

当前 `activation_v5_independent_review_passed=false`，wrapper/review/dispatch/pilot/formal/result/claim/security 均为
false，`user_formal_run_authorized=false`。本轮未运行 production worker、loader、solver、pilot、formal 或 activation；
下一步仅独立 R4 review。

### 2026-08-31 activation-transport v5 PASS 与 execution-controller successor v1（review closed）

独立 `sol_reviewer` 对 v5 的最终 verdict 为 `PASS`，Blocker/Major/Minor 均为空。machine receipt
`configs/rq2_public_grid_two_block_pilot_activation_transport_review_pass_v5.json`（SHA-256
`7378202388554a31ce4fd89ae6a9b7fec64360bc2c02cb8b916c936716c3d2c5`）精确绑定 v5 outer
`2afd26332d4965de625e46d8fdac3083559e5b6d8925876c00866ff368451e48`。该 PASS 只授权创建并以
0-solver 方式审查新的 versioned execution controller/worker successor；不授权 execution、pilot、formal、result、
claim 或 security。

successor v1 使用独立 controller/worker transport，不调用任何 predecessor closed dispatch/worker。未来 production
worker 只调用 sealed v4 `_stage_context/_load_worker_data` 与 recovery-v2 `_process_block/
_validate_scientific_payload`，controller 将真实 Popen PID/create-time、匿名管道 ACK、source payload/attempt-receipt
bytes 与 v4 `AcceptedEvidence/ControllerLedger` 绑定后，才可交给 sealed v7 `_publish_result`。固定顺序仅为 0008→0009；
每个 index 在 spawn 前由 `RLock` 原子消费，失败不 retry，0008 未形成 exact accepted evidence 时 0009 不可启动。

资源合同保持 v5：preflight available commit `>=10 GiB`；runtime 每 5 s 同一 sample 检查
`child_private >=8 GiB`或`system_available <=2 GiB`；watchdog 为 21600 s。timeout、sampling error、resource stop、
nonzero、missing/incumbent 或 unresolved 仅为 honest incomplete，绝不推断 infeasible；仅终止 exact owned
PID+create-time child。review-only exact child E2E 使用 locked Python 与 successor worker command，完成
HELLO/frame/EOF/ACK 后在 loader 前返回 `NON_ACCEPTED_PRELOADER_BOUNDARY`，四类执行计数均为 0。

唯一未来 review authority 是固定 lexical path
`configs/rq2_public_grid_two_block_pilot_execution_controller_review_pass_v1.json`；当前该文件不存在、不可由 CLI
配置、不可自签。未来 receipt 必须精确绑定 successor outer 与完整 chain，并保持 formal/claim/security false。
config/controller/worker/bootstrap/tests/inner/outer SHA-256 分别为
`e2bd40c96d56ac0e6cdbc50b267c41d61f8d5dc7f358825b41434e56abf7ec43`、
`e4fca5827bab656239be539ff5500b3dec088e0250eed3630cde391c13a1c365`、
`ef923aaaf15a1760c52e61bf81e4c3a8e20deab121f6b61d3f127e42464f55a6`、
`4ede07bc20f3bad0ddcb56b2dd2538d96ea986dfc4d7e608b230fa2b98aea45b`、
`121d940a2342584996995f44335459c4d970d732c81beb6c90313c88191bf928`、
`7af17d5d10ae63bffc27ac7176b1ae0b36f26389c89c2865caede54bc9d0450f`、
`c21ced8b52f5aeaa3e6720991d871ccb6ae6ff513f506adf41a5bb436e2154bd`。

final focused `26 passed`，v1–v7 candidate、activation/transport、execution-successor 与 recovery-v2 full related
`464 passed`，Ruff 通过。canonical sanitized-env bootstrap/controller validate-only 均返回
`validation_passed=true`、`execution_review_present=false`、`execution_ready=false`，且 0 project/science import、
0 worker、0 loader、0 solver、0 result/formal write；canonical `--execute` 因固定 receipt 缺失在 controller import 前
exit 1。当前 successor 状态为 `execution_controller_successor_v1_review_closed`；independent review、execution、pilot、
formal/result/claim/security gates 均为 false，`user_formal_run_authorized=false`。下一步仅独立 R4 review，不执行。

### 2026-08-31 execution-controller successor v1 REWORK 与 v2（closed）

独立 R4 reviewer 对 v1 给出本周期唯一 `REWORK`：v5/v7/recovery/candidate-v4 的 runtime 依赖闭包未在
bootstrap 与 worker loader 边界完整展开复核；固定 review receipt 未在 bootstrap/controller/worker 三入口执行
同一 exact object/effect contract；`solver_calls` 仍是公式估算而非由 validated payload 的实际 baseline、primary 与
zero-DC confirmation 证据机械统计；科学/发布测试未完整经过 live closure 与 registered orchestration seam。
machine-readable receipt
`configs/rq2_public_grid_two_block_pilot_execution_controller_review_rework_v1.json`（SHA-256
`a24f0d5a3c22b03ce2d3eaeaa20c644b819f491fd338f50e156b8f8098499135`）精确绑定 v1 outer
`c21ced8b52f5aeaa3e6720991d871ccb6ae6ff513f506adf41a5bb436e2154bd`，且不授予执行权限；v1 全部 sealed bytes
未修改。

versioned v2 的 stdlib-first bootstrap 在 controller/science import 前递归展开并 live-verify：immutable v1、v5、v7、
candidate-v4 的 outer→inner→exact members，recovery-v2 exact 7 members，以及 provenance contract 登记的 12 个
transitive source paths；严格逐段 lstat、ordinary-file、no symlink/junction/reparse/nested-mount、double-read/hash。
worker 在 HELLO 前和 actual loader 前重复同一 closure gate。固定 future review receipt path 为
`configs/rq2_public_grid_two_block_pilot_execution_controller_review_pass_v2.json`，三入口均要求 exact keyset、
exact outer/predecessor/closure binding，且 effect 唯一允许 nonformal two-block=true，formal/claim/security=false；
当前 receipt 不存在，不可由 CLI 指定或自签。

`solver_calls` 仅从 recovery validator 已接受的 canonical payload 机械重算：no-event baseline/primary 的
`not_applicable_no_active_outage` 计 0；实际 baseline solve、active-event primary solve、每个非空且成对的
zero-DC confirmation 各计 1。冻结 synthetic 表为 no-event=0、单 finite event=2、单 E0=3、三个 E0=7；任何
missing/extra/malformed/pair mismatch 或 worker/controller accounting mismatch 均在 acceptance/publication 前拒绝。

当前封存 SHA-256：config `de75329751fd78651d280f11799282fbf1e77f360dc13ea17c34a10fea4fab6c`、
closure `fb0857c239ecfe4014579b91924e3a14844e366f63ba89803ea3e3bc6eaf753f`、bootstrap
`6f8398d0ca00dbd88eae775eeb83404fe36c4f5ca2d9d340d5b84618389c5786`、controller
`3716e21b32044b31c8ef8d395adab4c788dab8b17532222e7d5a2a77e9457b34`、worker
`4dbe7992050dd405911b0ca45f9d69f6af2d0aa4365939cb29b12d39e0e04c7a`、tests
`c624fafb1ef668921bec9a40048f94d94177871b1b27ee4b44bd76690211e8a9`、inner
`4efc24caeeca09745d82c594d32c931a705bd9a7ad14e38e3e64418899a5a201`、outer
`9c2822fef43e34743e12f79fb4fd3545812a2cb797bb74d50ed132be15bf44c0`。

focused `75 passed`，全部 two-block related 加 recovery-v2 `539 passed`，Ruff 通过。真实 direct-module
`--review-preloader` E2E 返回 `NON_ACCEPTED_PRELOADER_BOUNDARY`、`accepted=false`、四类计数全 0 且 child 回收。
canonical sanitized-env
bootstrap `--validate-only` 返回 `validation_passed=true`、`dependency_closure_verified=true`、
`execution_review_present=false`、`execution_ready=false`，以及 0 worker/loader/solver/result/formal write；同环境
`--execute` 因固定 receipt 缺失在 controller/science import 前 exit 1。当前全部 independent-review/execution/
pilot/formal/result/claim/security gates 仍为 false，`user_formal_run_authorized=false`；未启动 production worker、
loader、solver、pilot、formal 或 activation。下一步仅为独立 R4 review，状态为 `READY_FOR_INDEPENDENT_REVIEW`。
### 2026-08-31 execution-controller successor v2 ESCALATE 与 v3 live-closure remediation（closed）

execution-controller successor v2 的独立 R4 审查正式为 `ESCALATE`：v2 只在
bootstrap/worker-loader 前验证 dependency closure，不能排除 solve、validation、worker
write、controller acceptance 与 publication 各边界之间的 live-byte drift；solver-call
accounting 也未同时冻结并验证 `termination_condition + solver_status` 的合法组合；零 solver
orchestration 仍允许 caller 提交 validator/publisher callable，未证明 actual sealed v4/v7
integration。machine-readable receipt
`configs/rq2_public_grid_two_block_pilot_execution_controller_review_escalate_v2.json`（SHA-256
`6961754a46c0a868fb08f84855403e5e54e18a091b12a286c8c02eb5f8ce000f`）精确绑定 v2
outer `9c2822fef43e34743e12f79fb4fd3545812a2cb797bb74d50ed132be15bf44c0`，不授予执行权限。

versioned v3 candidate 在八个边界执行完整 recursive closure double-read：bootstrap 导入
controller 前；worker loader 前、solve 后/validator 前、validator 后/write 前、write 后/ACK
前；controller child 返回后/ledger accept 前、0009 后/publisher 前、publisher 返回后。任一
pre-publication drift 均阻止 acceptance/0009/publication；post-publication drift 明确归类
`commit_indeterminate`，强制 `published=false/claim=false/formal=false`，不删除或覆盖已经出现的
result/success artifact。accounting 仅统计冻结的实际 solver-invoked pair：baseline 与 finite
primary 接受 `optimal|globallyOptimal + ok`，E0 primary/zero confirmation 只接受
`infeasible + warning`；no-event `not_applicable` 不计调用。冻结 Gurobi 0008 经 actual recovery
validator 校验并机械计为 3 次调用。

actual integration 测试使用 sealed v4 `_validate_scientific_payload`、`AcceptedEvidence`、
`ControllerLedger`、memory-evidence revalidation 与 sealed v7 `_publish_result`/
`load_verified_success_commit`，仅在 pytest `tmp_path` 写临时 publication artifact，不触及项目
result roots。focused `36 passed`；全部 two-block related 加 recovery-v2 `575 passed`；Ruff
通过；canonical sanitized-env bootstrap `--validate-only` 返回 `validation_passed=true`、
`execution_ready=false` 和 0 worker/loader/solver/result/formal write。

v3 config/contract/bootstrap/controller/worker/tests/inner/outer SHA-256 分别为
`1aae6989cdefdef84ef8de7fc9cea56a2464b36f250e19ea37781526792c2428`、
`17714b6ee759749f3085e53c2410d1eed0ba5adf37ee226ca828d0579ff871ec`、
`42d190882b6dcf5c9dac1f3cd4ac84e2b6980fa31773c4f4454ffc0d7d6863c8`、
`c10794a0f6ae8cec7f0744017325f6cf0255f8a8f103753a00d8e5d09e21a2af`、
`4b898326f08b6991754d61f89021041a31843dfe82fee3ff4decee8be9068a76`、
`36f2a82b2e5443013298d014dc726163a06dfd05f109a1692a8a18a1785467cd`、
`a9792edf7c9b8a94f2b92fa8ae7001fa3e9afe62de9ad8bfa87d8d280ed5bc48`、
`bc6fb4b1d6999a0e38323b7605f16103f70fe27fc904fdd98ce28ec6a7b60976`。
当前 v3 independent review receipt 不存在，所有 execution/pilot/formal/result/claim/security
gates 仍为 `false`，`user_formal_run_authorized=false`。本轮未启动 production worker、solver、
pilot、formal 或 activation。最终 production 可达性审计发现：controller 的 `--execute` 分支
无条件 fail closed，worker 即使未来 fixed review receipt 存在也仍无条件返回“production transport
review closed”；当前没有 controller-owned pipe/dispatch、真实 `AcceptedEvidence` 构造、ledger append
再到 publisher 的 production wiring。sealed v7→v4 publication 链会执行
`_revalidate_memory_evidence→_validate_worker_result`，但不会在该处重调
`_validate_capability_envelope`，所以不存在已经证实的 v4 command-field 不兼容；缺口是 v3 transport
根本未实现。pytest 中 actual integration 使用合法 v4 fixture，只证明 validator/ledger/publisher
边界本身，不证明 v3 production 可达。因此当前诚实状态为 `ESCALATE`，不得生成 v3 review PASS
或启动执行；下一步需独立 blocker audit 决定 versioned transport successor 的范围。

### 2026-08-31 execution-v3 ESCALATE 与 evidence/publication successor v1（closed）

execution-controller successor v3 因 production transport 无条件关闭、actual integration 仅消费既有
v4 fixture ledger、未形成 controller-owned transport→evidence→ledger→publication 连通链而正式
`ESCALATE`。machine-readable receipt
`configs/rq2_public_grid_evidence_publication_successor_review_escalate_v3.json`（SHA-256
`134a774f415642fff52583f7e464bfb86555e7bc353b92fdee15678cbf4a5aa7`）精确绑定 v3 outer
`bc6fb4b1d6999a0e38323b7605f16103f70fe27fc904fdd98ce28ec6a7b60976`，不授予 pilot、formal、
claim 或 security authority；v1–v3、candidate-v4/v7 和 formal artifacts 均保持不可变。

新的 versioned successor v1 自有 `AcceptedEvidenceVnext`、`ControllerLedgerVnext` 与
`ControllerReceiptVnext`。仅 controller 能创建 exact locked worker command/cwd/sanitized-env 与
匿名管道，消费真实 HELLO、单 envelope+EOF、ACK、source result/attempt-receipt/scientific bytes，
并以 session-key HMAC 深冻结 PID/PPID/create-time、nonce、block/index/predecessor、module/config/
chain hashes 和所有 byte/hash identities。ledger 在 spawn 前原子消费 attempt，拒绝 concurrent/retry/
replay/reorder/swap/cross-session；0009 仅由同一 session 内已接受的 0008 digest 解锁。公开 API 不接收
Popen、caller evidence 或旧 v4 transport evidence。

新 publisher 不调用 v7 `_publish_result/_validate_result_contents` 或 v4 ledger；仅复用 v7 已冻结的
统一三路径 presence snapshot/path probing。它自行重验 Vnext transport/science/source bytes、写 exact typed
tree manifest，并以 result directory rename 后的独立 success-directory rename 作为唯一 success commit。
pre-commit failure 只清私有 staging；result appearance 后的 closure/tree/race 异常为
`commit_indeterminate`，不得删除/覆盖、不得创建 terminal、不得 resume，也不构成 infeasibility evidence。

真实 zero-solver E2E 在 pytest 临时目录顺序启动两个不同 PID 的 exact worker。worker 使用冻结 Gurobi
0008 predecessor payload 机械派生并经 recovery-v2 validator 接受的 nonformal review fixture；0008/0009
canonical payload SHA-256 分别为
`ae9d068e74c6809e2b2a6f43f0643cad2c7dcfb1def3e5e522d602774f2d5868` 与
`7714099e5b6500ee4e469150eb000e4a56b3215da57db530761f80a41ab11ef2`。这些 artifact 始终标记
`review_fixture=true/nonformal=true/claim=false`，loader/solver calls 均为 0，不能外推为 production result。

封存 hashes：config `63b746841c272d39e5d379c600baa4e60c027d80617f7fac655ca14f7542eb3a`、
inner `7c573ade9f031e039e6eb8873c40638006c4b137c6a0bafccd14a951ee6546ba`、outer
`f255626708654b22d14b4c881921ff6f11646122de804582f1ef42bc65ac24c4`。focused `21 passed`；
recovery-v2/candidate-v4/v7/resource-v5/execution-v3 related `185 passed`；Ruff 通过。canonical bootstrap
`--validate-only` 返回 `validation_passed=true`、closure inventory 17、0 worker/loader/solver/result write，
且 `execution_ready/formal/claim/security=false`。当前状态仅为 `READY_FOR_INDEPENDENT_REVIEW`；future
production API/review receipt 仍关闭，未启动 production worker、loader、solver、pilot、formal 或 activation。

### 2026-08-31 evidence/publication successor v1 REWORK 与 v2（closed）

独立 R4 reviewer 对 v1 给出本周期唯一 `REWORK`。machine-readable receipt
`configs/rq2_public_grid_evidence_publication_successor_review_rework_v1.json`（SHA-256
`65c2f291eda3044a7794a4cce8dfe0542fd8f6e7e10b835a9a1df793f07b9757`）精确绑定 v1
outer `f255626708654b22d14b4c881921ff6f11646122de804582f1ef42bc65ac24c4`，不授予
execution/pilot/formal/claim/security authority；v1 全部 sealed bytes 保持不变。

versioned v2 将 runtime HMAC key 与 session authority 仅保留在 controller 调用闭包内，公开
review API 只返回不可变 `ReviewOutcome`。普通 import 不暴露可组合的 evidence factory、append、seal、
accept 或 publication authority；完整两条 fake record 加 controller receipt 即使具有 exact schema、
raw frame/source/science/closure/pipe 字段，也因不能生成闭包 HMAC 而在 result 出现前拒绝。真实
review fixture 则由 controller 独占 spawn 两个 fresh worker，并将 HELLO/envelope/ACK/result/
attempt-receipt 原始字节、PID/PPID/create-time、raw handle type/direction/inherit role、block/index/
predecessor/session/nonce、exact argv/cwd/env/module/config 和完整 closure path→SHA256 mapping 纳入
record/receipt HMAC 与 publication 前后重验。

v2 publisher 不调用 v7 classifier；config 冻结三行 machine truth table，独立实现为：三 leaf 均 clean
absent 且 ancestors ordinary 时才是 `honest_incomplete`；只有 exact V2 result + exact bound success 且
terminal clean absent 才是 `committed_success`；任何 unsealed result appearance、terminal appearance、
alias/reparse/unreadable/corrupt/mismatch/dual state 均为 `commit_indeterminate`。result 与独立 success
directory 均经 typed-tree、source/science/evidence/controller-receipt/closure mapping exact reread和 atomic
rename；pre-result failure 不发布，post-result/post-success 不确定状态不删除、不覆盖、不创建 terminal，
也不推断 infeasibility。

封存 SHA-256：config `cbb617566fd968174573a124443bf77a8496a0e2ae8b806bf5a036ed25d3ebae`、
contract `e3c36f6d6f1acbae0ae62105d6f9d7ac3b63b60472c598196bd0819722212a1c`、controller
`54979a0de2d369db287976bece2e03249989efa2f25c81233813b35a71b65cf7`、worker
`9f1f831a36db18d8fc8a1979d1865eb735f1eef0ad3d5d574880db15dfec240f`、publisher
`e7d7a36ac990d7fb6be3672df47fa1f55acb5da03dfc1d5f3190fc9819094707`、bootstrap
`32226c0915801e19ad0b4a9de7d3b784d5e03e800bbdd2b1717a9f373ab6a2ca`、tests
`5ce6a3d968916fbc5a89b280a63de243b13a60ae3204d6f933887bdd51b19a65`、inner
`ae05ffc010b909a4e9fdbcba4fd46ec30a86187dc1a63010ba4c8c770a294569`、outer
`693422c44d87fd230bcc2316ad87db9274025fd61ea354b7b679cc1afe8183ee`。

验收：focused `33 passed`；v1/v2 evidence、execution-controller-v3、candidate-v7、activation-v5 与
recovery-v2 related `184 passed`；Ruff 通过。canonical bootstrap `--validate-only` 返回
`validation_passed=true`、closure inventory `27`、closure mapping
`c699ef5c3856741fca5926a6882d26b719b3dbe88cac78cff5151914652eb2c4`，且 worker/loader/solver/
result writes 全为 0、`execution_ready=false`；`--execute` 在 bootstrap import gate 处 exit 1。
当前 `independent_review_passed/execution_ready/pilot_executed/formal_execution_ready/
user_formal_run_authorized/formal_result_exists/claim/security_certified` 全为 false。本周期只运行
pytest 临时目录内的 review fixture worker，未启动 production loader/solver/pilot/formal/activation。
状态为 `READY_FOR_INDEPENDENT_REVIEW`，不是执行许可。

### 2026-08-31 evidence/publication successor v2 ESCALATE 与 v3 exact-closure candidate（closed）

v2 独立 review 正式 `ESCALATE`：其 closure provenance 经 v1 的 lossy path-only wrapper 后只有 27 项，
未直接保留 sealed execution-controller v3 authority 返回的 68 项 `path→SHA256` trace；v2 测试只检查
inventory 下界，因而不能证明 transitive 项无遗漏、重复路径无 hash 冲突或 stable-read drift 会
fail closed。machine receipt
`configs/rq2_public_grid_evidence_publication_successor_review_escalate_v2.json`（SHA-256
`34ae7072367aba3d72aef0966e01f8d28b54c424e85f61232806e956b1102e5d`）精确绑定 v2 outer
`693422c44d87fd230bcc2316ad87db9274025fd61ea354b7b679cc1afe8183ee`，不授予 execution/pilot/formal/
result/claim/security authority；v1/v2 sealed bytes 保持不变。

versioned v3 只修复 closure provenance/exactness。它在 stable-read 校验 sealed authority module/config 后，
直接调用 execution-controller v3 的 `verify_full_live_closure(..., trace=...)`，要求 authority 返回路径集
与 trace mapping 完全一致，且 trace 为 exact 68 项。然后独立并集：该 68 项、v1 exact
outer/inner/8 members、v2 exact outer/inner/8 members，以及 v3 的 7 个 non-cyclic self members。
重复 path 只有 digest 相同才可去重，digest 冲突必须拒绝；最终 exact set 为 95 项，canonical mapping
SHA-256 为 `2c2969b97442165f212562e752830a81d6213978ca0501578aa814f20dc1e21f`。

v3 非循环封存规则为：inner 精确封存 config、v2 ESCALATE receipt、contract/controller/worker/
publisher/bootstrap/tests 共 8 项；closure mapping 的 self 部分只包含后 7 项，不将 v3 config/
inner/outer 纳入自身 mapping digest，而是由 inner 绑定 config、outer 再绑定 inner，避免自哈希循环。
evidence HMAC、controller receipt、result manifest、success/readback 仍使用 v2 的封闭 authority 和
publication truth table，但现在均绑定 exact 95 项 mapping 及 digest。科学 payload、certificate、
transport、resource、atomic publication 与 honest incomplete/commit indeterminate 语义未改。

封存 SHA-256：config `fc6f2c26c8d6cfcaac1047110c7db04d1ece946825d7c10cc0c8b416dd927f67`、
contract `f7365521e9168770bf93121f4a6efae521403d6d435095145709e01ae9c74f0d`、controller
`60356ca212d45a50a284ca796fa02461c50b04b7fcbd13009bfb0b069a34d06f`、worker
`9ec1c2bf103d25cbe3176ed3e886c294f84dea033751f73e1439dd3a69ccf3f9`、publisher
`9c7dd4a3662a117c85b0b83547d2d10db7c28c86897746837a00838544b3e304`、bootstrap
`49c446cffb49bba5c7e79056725e256445dcae7432161603305d8d0e72f5de8b`、tests
`f0763275060d1a781bfe94d7e71351a6addd4e05045f7122ec9fccda9c08104a`、inner
`afc16b8af6305e9aa5ce25a98c3cde075fd4cf852a5974ac584e6d74d8d2f949`、outer
`4b84fc86337ec82d6018bfe9c87bf23a75892afbf3d61e66b0a34549b0858ce7`。

验收：test-first 先因 v3 contract 不存在而 collection error；修复后 exact-set/omission/hash drift/
duplicate conflict/stable-read 定向 `5 passed`，focused `38 passed`，related `222 passed`，Ruff 通过。
canonical `--validate-only` 返回 `validation_passed=true`、inventory `95`、上述 mapping digest，且
worker/loader/solver/result/formal writes 全 0；negative `--execute` 在 bootstrap gate 处 exit 1。
当前 `independent_review_passed/execution_ready/pilot_executed/formal_execution_ready/
user_formal_run_authorized/formal_result_exists/claim/security_certified` 全为 false。本周期只运行 pytest
临时目录内的 review fixture worker，未启动 production loader/solver/pilot/formal/activation。状态为
`READY_FOR_INDEPENDENT_REVIEW`，不是 PASS 或执行许可。

### 2026-08-31 evidence/publication v3 PASS 与 nonformal execution successor v1（review closed）

独立 R4 reviewer 对 evidence/publication successor v3 的最终 verdict 为 `PASS`，无 Blocker/Major/Minor。
machine-readable receipt `configs/rq2_public_grid_evidence_publication_successor_review_pass_v3.json`
（SHA-256 `f486e862e7caa7985dbed182163d68c6c4f6a044f233eef06e94d314da535de6`）精确绑定
v3 outer `4b84fc86337ec82d6018bfe9c87bf23a75892afbf3d61e66b0a34549b0858ce7`、68 项 sealed
execution trace（digest `0b7652f73b84b3885a8f0d51a4c3eb909b553bc67e54ce38fed6f389b4740b54`）和
95 项 exact successor closure（digest `2c2969b97442165f212562e752830a81d6213978ca0501578aa814f20dc1e21f`）。
该 PASS 只授权创建并以 0-solver 方式审查新的 versioned successor，不授权 execution/pilot/formal/result/
claim/security。

新 successor 固定为 nonformal `holdout_s20260822_0008 → holdout_s20260822_0009`，每个 block fresh child，
spawn 前原子消耗 attempt，禁止 retry/resume/reorder/skip；0009 仅由同一 session 已验证并持久化的 0008
accepted-evidence digest 解锁。未来 actual science worker 使用 locked audit Python 和 exact module/argv/cwd/
sanitized env，调用 sealed `_stage_context/_load_worker_data → recovery-v2 _process_block →
_validate_scientific_payload`，并将完整 scientific bytes/hash、certificate 与机械 solver-call accounting 绑定进
V3-derived HMAC/pipe/PID/parent/closure evidence。资源合同保持 preflight available commit `>=10 GiB`、同一
5 s sample 下 `child_private >=8 GiB` 或 `system_available <=2 GiB` 即停止、每 block watchdog `21600 s`；
timeout/resource/nonzero/missing incumbent/unresolved 均只作 honest incomplete，绝不解释为 infeasible。

publication 保持 V3 unified presence/truth table 与唯一 atomic result+success commit：staging、result rename 后、
success staging、success rename 后均重验 typed exact tree、source bytes、receipt/HMAC、closure 与 summary；最终
live closure 再验后才可 `committed_success`，任何 post-appearance 不确定性均为 `commit_indeterminate` 且
`published=false/claim=false/formal=false`。固定 future review receipt path 为
`configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_review_pass_v1.json`；当前文件不存在且不在
non-cyclic bundle 内，不可由 CLI 指定或 successor 自签。`--execute` 因其缺失在 controller/science import 前
fail closed。

封存 SHA-256：config `dc24d685c826c4693abe6ad191e3fc4de12e433e13183b10ab50530fd604faf0`、contract
`80054e940fca83c220464f2690c01d107d9b8d89372708196e708ac0416edc0d`、controller
`3ef2242b7b3bd5281c44669553e7f0b398bef7430a7fe10d6be6135b313a1651`、worker
`322ccc768efd8455aced3262dee0b20c5f548b7e71071f0cd2c66649c942da1f`、bootstrap
`c26131a95188beff89765a865e14d885a6e3c6de591af92f7d29845381bbe49e`、tests
`2e304dc82693e4dfc0a83079d8e84676adc59213098f2483153ad6b54020a8b0`、inner
`7924670bbbbbbf42688ec6a7546d352c1693850a738f04fdff4239e1994c0522`、outer
`f6874ef26b0ab13287fd6050c2617da65545fa19ffd3ea8bd92917af158fbb49`。

验收：test-first 红灯为 missing contract；focused `23 passed`，相关 7 文件 `205 passed`，另显式
candidate-v7 path/presence 回归 `40 passed`，Ruff 通过。canonical direct-script `--validate-only` 返回
`validation_passed=true`、V3 closure `95`、live authority `96`、0 worker/loader/solver/result write、
`execution_ready=false`；negative `--execute` exit 1。formal runner/config 与 9 个 Gurobi checkpoints 哈希不变，
5 个新 roots 和 fixed review receipt 均不存在。本周期只运行 review-preloader child（已回收），没有运行
production worker/loader/solver/pilot/formal/activation。当前状态 `READY_FOR_INDEPENDENT_REVIEW`；所有
execution/pilot/formal/result/claim/security gates 仍为 false。

### 2026-08-31 Vnext execution successor v1 REWORK 与 v2（review closed）

独立 R4 对 v1 的正式 verdict 为 `REWORK`：其 runtime 未直接验证 successor 自身 outer→inner→成员
闭包，且 HELLO/envelope/ACK/result/attempt receipt 缺少逐消息 exact-keyset 与完整 cross-binding。v1 bytes
保持不变；machine receipt
`configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_review_rework_v1.json`（SHA-256
`12ad4866243e1276e0b4e2454c7f9823748ec906cfd7b1958042ee0343d9a0b6`）精确绑定 v1 outer
`f6874ef26b0ab13287fd6050c2617da65545fa19ffd3ea8bd92917af158fbb49`，不授予执行权限。

versioned v2 新增非循环自封：outer 只绑定 inner，inner 精确绑定 config、v1 REWORK receipt、contract、
controller、worker、bootstrap、tests 共 7 项；runtime 每次重读并核验 9-path self mapping（outer+inner+7
members），再与 V3 95-path closure 和 frozen activated config 合并为 exact 105-path live authority。controller/
worker/bootstrap/config hashes 只取自 inner manifest。HELLO、envelope、ACK、result、attempt receipt 均使用
exact schema/keyset，并 cross-bind session/index/block/predecessor/nonce、PID/PPID/create-time、exact argv/env/
cwd、pipe roles/type/direction/inheritance/handles、self/V3/live mappings、raw message/source hashes、scientific
payload hash 与 solver accounting；同一 scientific payload hash 贯穿 ACK、accepted evidence、controller receipt、
result manifest 和 success readback。科学链、0008→0009、V5 resource limits、honest-incomplete 与 V3 atomic
publication 语义未改变。

封存 SHA-256：config `e742af10dd8990391d0e87af865394170b02d86a0611773d4321dab1415c3bf2`、
contract `78daacf2a0680d36c9ca5d1b2450ad667cbcd9daf0f9cf69332d7b8fb9a71006`、controller
`4366f37ae12ccc9c80b560d640ee65ea97c49387c01c602648a88e0ca2509b01`、worker
`2f98177b3482c06e309ecea3133dbca16e390f8723f1eb1a6ed1a1ab7091ebd7`、bootstrap
`00c6a2268fc08633f3527e7f5f912eb2d366540f802a2107042cdc56544e6e3f`、tests
`0878f432284f52531ac93904034aa03eeac12f5c1e98739f54ca23dbd0b2d9c3`、inner
`d5129434345625b4eee3a8e6f29317115e681e41526bb23287385f47c9af8147`、outer
`526e38c6194ece2f41f0f260f80dd2bb5ddcfa3115fad80e1552eb26e1425009`。

验收：test-first 首个红灯为缺失 `verify_self_bundle`；focused `39 passed`，7-file related `245 passed`，
candidate-v7 `40 passed`，Ruff 通过。canonical `--validate-only` 返回 `validation_passed=true`、V3 `95`、
self `9`、live `105`、0 worker/loader/solver/result write、`execution_ready=false`；negative `--execute`
在 fixed v2 review receipt 缺失时于 bootstrap gate exit 1。当前仅 `READY_FOR_INDEPENDENT_REVIEW`，未生成
PASS receipt，未运行 production worker/loader/solver/pilot/formal/activation；所有 execution/pilot/formal/
result/claim/security gates 保持 false。

### 2026-08-31 Vnext execution successor v2 R4 PASS 与资源 preflight 阻塞

独立 R4 对 v2 的最终 verdict 为 `PASS`（无 finding）。fixed exact 10-key authority receipt
`configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_review_pass_v2.json`（SHA-256
`20154618e4dad98b2c65ae811debf7ec43cbed9ebf6f5fef8abc7d5b7ca607fb`）通过 sealed bootstrap 与
contract 双重验证；它绑定 v2 outer
`526e38c6194ece2f41f0f260f80dd2bb5ddcfa3115fad80e1552eb26e1425009`、V3 outer/PASS 与 exact effect，
只打开 frozen nonformal 0008→0009 pilot gate，formal/claim/security 均为 false。审计 companion
`configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_review_evidence_v2.json`（SHA-256
`afa52ab4d4ad0ed1e5d8cca9242f5a847a51cc55abe82b8d838691785d599fd1`）明确标记
`authority=false`、`not_hash_bound_by_execution_receipt=true`、`opens_execution_gate=false`，本身不授予权限。

同一 live preflight sample（`sample_time_ns=1788179355896000000`）观测 available commit
`5,679,972,352 bytes = 5.289886 GiB`，低于冻结前置门 `10 GiB`，因此 `preflight_pass=false`。其余门均
通过：related process 为 0，5 个 V2 roots clean absent，self/live inventories 为 9/105 且 digest 精确，
formal runner/activated config、locked Python 与 9 个 Gurobi checkpoints 均保持冻结 hash。依据 fail-closed
合同没有调用 canonical `--execute`，没有启动 worker/loader/solver/pilot/formal，也没有写 result。receipt
保留；只有 available commit 恢复到 `>=10 GiB` 后，重新完成同一时点全量 preflight 才能开始 nonformal pilot。

## 2026-09-01 Vnext v2 post-result REWORK 与 v3 证据门

上面的 v2 preflight 记录是历史时点。v2 之后已完成 nonformal 0008→0009 atomic publication，但独立
post-result review 为 `REWORK`。正向事实是 publication classifier 为 `committed_success`，result/success typed
trees 精确，terminal absent，两个 scientific payload 均被 controller 接收；这不等于 post-result PASS。
正式 blockers 是资源门没有留下完整 same-pair sample sequence/aggregate，以及 session HMAC secret 销毁后产物
不可由 reviewer 独立验证；majors 是计划/登记仍写成未执行，以及没有 worker 时点实际 highspy/runtime version。
REWORK receipt SHA-256 为
`18517b489929503aa4f1cfd03f6e1f7f76a38d2a9ffa6a41def208f26b91fa75`，v2 result manifest/result tree/
controller receipt/success/success tree SHA-256 分别为
`9cbc808de79a842c252bb1b2f3c09d81119c686bf9da00cf36941aa970b4ea28`、
`b7fb776a48db2964e0372d07389051c9bcc6a4feef2dc82f261dadb09d53a3b3`、
`dc1cf2bf7e8deb205f234cc4054fb2218e9cb49033ad8641f8a0e05104e60d53`、
`75e565f5cd8f9c0336fa101fb4d8bd3aed5e355f1fa5c0fa67d1732930833612`、
`a511af614715dfe1ec02c002ff37411249650a47eaa18b12f3823125b9e62a18`；全部原字节保留。

v3 是新的 evidence run successor，不是 v2 resume。它保持 0008→0009、fresh child、no retry/resume/reorder/
skip、V5 10/8/2 GiB 门、exact 5 s scheduled cadence、21600 s watchdog、HiGHS 1.15.1/4 threads 和同一
scientific hook/config 不变。science envelope 必须等待 first same-pair sample；每条 sample 的 wall/
monotonic/scheduled time、PID/create-time、private/available commit、阈值和 computed stop reason 以及完整
aggregate 会贯穿 receipt/ACK/accepted evidence/controller receipt/result/success，并由一次性 Lamport signature
覆盖。worker 同时持久化实际 package/runtime version、solver options 和 locked interpreter/highspy binary hashes。

public anchor key id 为
`2aa72810e4581787f33df92480a684352e709b5c92f4089a8da2b3b49ef86183`，anchor file SHA-256
`00944590ff24d16307b2690169a6be746a2ff280232506dd94fc65fdd6237132`。旧 key machine state 为
`REVOKED/never_authorized/never_used` 且旧 fresh lease 不存在；新 private lease 仍 fresh/unconsumed，不在 bundle
或 tool/test artifact。普通 import 不持有 production signing authority，运行后只允许无 seed tombstone 与可独立
验证的 public signature。威胁边界明确为
`same_os_user_pre_execution_lease_exfiltration_out_of_scope=true`、`security_certified=false`，不能用于安全声明。

v3 config/contract/controller/worker/bootstrap/tests/inner/outer SHA-256 分别为
`50ede12f2b4e6428f56a58caaf0082a6adbbba6dd059ef13617777b05895a4e3`、
`c72fdbb08b8c4a9eb28c558238f1363921abbc61b5dfd114d91bb0e3dca23d82`、
`6e9b569995ea3176f69f7970fd4ed56ec4d571ddfabea5c1ea73f82183e35d51`、
`cb3ebc90e9d0cd4ad384026fc88538168a2d3a5d83fc436ed22b2cbbed97de7e`、
`2fad06ad48eb0a43a416c8807a05162b0fc69bddb3bdd36dfc52d32d087dd514`、
`203ae7d6bed6739fe7e68d8af8695543e3c4777d6c15a39724a7d7d731f1d98b`、
`8dab5255b4ee750c37afdcf4315c60f43089a80cd45b1a4cdee3449577513a26`、
`017ca2c339974f1f33e14e141a0f48bbe528f927b585b9d8596d6f0b8fd04421`。focused `36 passed`；current-state
related `329 passed, 5 deselected`，5 项均是 sealed v2 pre-run absent-state 测试与现存 PASS/result 的历史前提
冲突；未过滤的 broad run 为 `329 passed, 5 failed`，没有把历史状态冲突隐藏成实现通过。canonical self/live
为 `11/142`、future v3 PASS receipt absent、fresh lease present、consumed absent、
execution counters 全 0。当前 blocker 是“尚未取得独立 v3 pre-run PASS 与新 authority receipt”；因此没有运行
新 pilot/formal，`execution_ready=false`、`post_result_independent_review_passed=false`、
`formal_execution_ready=false`、`claim=false`、`security_certified=false`。

## 2026-09-01 Vnext v3 ESCALATE 与 v4 closed candidate

v3 独立 post-result evidence review 的正式结论为 `ESCALATE`。authority receipt SHA-256 为
`f53245d8bd920782a6bb6793b632be04dea2ca8c5c55c38623d030a2b222e394`，non-authoritative evidence SHA-256 为
`d34f2b1b03903288f7e0b47951a94cf4e0213c16d4742034399992e8f05aef58`。重复 blocker 是 100 s actual
observation gap 在 v3 中仍可被 scheduled labels/aggregate 一致性掩盖；major 是 post-rename lease validation 异常
可能留下 consumed raw seed。v3 outer/inner/public anchor 仍为
`017ca2c339974f1f33e14e141a0f48bbe528f927b585b9d8596d6f0b8fd04421`、
`8dab5255b4ee750c37afdcf4315c60f43089a80cd45b1a4cdee3449577513a26`、
`00944590ff24d16307b2690169a6be746a2ff280232506dd94fc65fdd6237132`，原字节未改。v3 key 已在不读取
seed 的条件下撤销；revocation/tombstone SHA-256 为
`efb58ebbafebcbc8794d70fb2ebeec402b1d034a31262c5fe57cca6ce14057e1`、
`2fad5efb1a4c640ecd12d1c27798518cf68f56a6adf0d3e35b12af0d047474d9`，状态
`REVOKED/never_authorized/never_used`，无 raw seed。

v4 保持全部科学配置与 0008→0009 语义，只新增预冻结 `1 s` OS scheduling audit jitter：5 s absolute slots、
actual `[slot,slot+1 s]`、actual gap `[4 s,6 s]`、no catch-up、exact due-slot count、last sample→exit `<=6 s`；
miss 只作 exact-owned termination + `honest_incomplete`。lease acquire 内部 finally 对所有 post-rename failure
point 无条件生成无 seed tombstone。v4 public anchor SHA-256/key id/commitment 为
`55bcb2c119d25381c8c6f3edb7a0d3ca2f49ede4e7836185ada3f3c908cf9a47`、
`d488f9ef76e86ac1cc7d385252937df76190adcb0fe10332ecf3504bed07b7ac`、
`ab4930c4bbb229686c19dd59e17a9a0866ca3f96b559f7710d3f32dade50c0d0`；production fresh lease 未读取、未消费。
威胁边界仍为 `same_os_user_pre_execution_lease_exfiltration_out_of_scope=true`、security false。

v4 inner/outer SHA-256 为 `3f70f046fec0acc9a1f22d59c58c1fb07c88c767446ddc782538c3d1fc2712ad`、
`36e6f9fd971601a157583a73b37f73470095f6ae2046294705865118f2695a1d`。focused `44 passed`、related
`302 passed`、signed-journal/readback 定向项 `1 passed`、Ruff 通过；fast probe count/expected=`1/1`，first sample 在 1 s 内且早于 release，0 solver/write。
当前 blocker 是“v4 尚未取得独立 pre-run PASS 与新 authority receipt”。future receipt absent，未运行新 pilot/formal；
`execution_ready=false`、`pilot_executed=false`、`post_result_independent_review_passed=false`、
`formal_execution_ready=false`、`claim=false`、`security_certified=false`。状态仅
`READY_FOR_INDEPENDENT_REVIEW`。

> Current-state supersession（2026-09-01）：上述 v5 candidate 随后的正式 verdict 已为 `ESCALATE`；v6 修复
> deadline/no-exit persistence 后，又在 broad load 暴露 authority rehash 落入首样本 deadline 的独立 regression。
> 当前唯一候选是本文件“Vnext v5 ESCALATE、v6 broad-load regression 与 v7 sampler-prebinding 后继”所登记的
> sealed v7（outer `7d3d6f08f2f73a0fe09639a76c5dde3c9b239ec11bd32b3113a45f85afb53d91`）。v7 仅为
> `READY_FOR_INDEPENDENT_REVIEW`，future PASS absent，未运行 pilot/formal，全部 gates 仍为 false。

## 2026-09-01 Vnext v5 ESCALATE、v6 broad-load regression 与 v7 sampler-prebinding 后继

v5 的正式独立 verdict 为 `ESCALATE`：exact `2 s` termination 若从 early previous sample 且在
deadline `+1 ns` 检出，会被固定 `8 s` last-sample cap 错分；同时 controller 可能先因缺失 exit notice/EOF
抛错，再取得 monitor future，令已形成的 honest deadline journal 未落盘。workflow receipt 与非授权 evidence
SHA-256 分别为 `cbce2ea6f31865bd5d5349dde35df219c14b3548c9a396998c77665f9b255683`、
`87d5812d1288790ebbfcfa76b0d2bc014fbb90c319057459a55376768e207341`。v6 修复了这两个 finding：deadline
分类改为实际 detection overrun `<=1 s` 与 exact-owned termination duration `<=2 s`；monitor future 只在 journal
atomic persist + stable readback 后完成；controller 对 exit-notice future 与 resource-monitor future 使用
`FIRST_COMPLETED`。v6 outer/inner 为
`39c13b6b7907272f8d6236b564f8e6c4be043922c3d785dcaebcfa4fb78aa7f6`、
`8d1e74ef695e7e3706a1255de64a5824412645ba46dba706a8176d9679dc3d5b`。

随后 current-state broad 暴露了新的可复现调度竞态，不是 child 提前退出：v6 的 slot callback 每次调用
`resource_primitives()`，连带重验 181-path live authority closure；20 次只读计时为约 `0.737–0.995 s`，broad load
下 sample completion 达 `1.016 s`。捕获 journal 的 status/reason 为
`resource_sample_deadline_missed/resource_sample_deadline_missed`、phase=`sample_completion`、sample count `0`、
detection overrun `16,000,000 ns`，且 exact-owned termination 完成。因此 v6 不能解锁 execution。该非授权
regression evidence SHA-256 为 `b1c9406cc6433a470fd1eb6cdedb6a32fe5ab1f41e9f54663f6c311869a59ced`。
v6 fresh key 从未获授权或使用，已在不读取 seed 的条件下撤销；revocation/tombstone SHA-256 为
`eff86e3a1fec26e6970364a3666c90a0bc813fe59cd7606c40d09f86091e242a`、
`4666ddbda23610aafe6d304a96723db2bed01c66382ebb70c014520bde9035a1`，fresh/raw-consumed seed 均不存在。

versioned v7 是独立后继，不修改 v6 bytes，也不改变 scientific hook/config、fixed 0008→0009、fresh child、
no retry/resume/reorder/skip、HiGHS 1.15.1/4 threads、10/8/2 GiB、5 s exact slots、1 s jitter、1 s detection
overrun 或 2 s termination grace。v7 在 monitor start wall/monotonic time 前完成 live-authority mapping 与 resource
primitive 绑定；每个 owned child/session 创建一次独立 sampler closure，slot callback 只做 exact PID/create-time
same-pair observation，不缓存资源数值、不跨 child/session 复用。exit time 记录后再执行 post-monitor live-authority
重验；journal 持久化 pre/post mapping digest、binding start/completion、owned identity、no-cache/no-reuse 与
verification status。digest mismatch 或 verification exception 也必须先原子落盘并 stable readback，再以
`controller_acceptable=false` 拒绝；只有 `child_exited` 且 mapping match 的 journal 可进入签名 success substance。

v7 public anchor SHA-256/key id/commitment 为
`70581261312bbe1d0d06515821cd968a8ee32c24bf7fa01bda7678f240bd4adc`、
`187ee2628b0e6e1c4fb3985f34e02881a3fed3381a31c94e2d52f1d042419023`、
`8d5064c4b8b9f8f9377a65bf5a158774e0dd3659a2e512351dfa6aab0d8704ca`。config/contract/controller/worker/
bootstrap/tests/inner/outer SHA-256 分别为
`22545ed0fe37d60f3a5c743922f569c0cefd270d53a3ecc43e737f5e0366ccb5`、
`c7b9f1b37ff1099f3a0b847a37b4824775b9e5bc616e7690dbb25f9930bf0b1f`、
`9ca62ecad1215ec30b41d9ab2f4b3b61dfff1859c53c5cb8ead66ade2d63f356`、
`741ff2d34c32372111aa139d3b354b72414b67a878c674b5153556dfbd8afeae`、
`cd2ffbe2566d10c089ccb3ac12a3adf3738c99a94a4e61748f97dda0e281b539`、
`2865443de4ee718c09ad072b199b659cce3af7e4bf7515d56ddcacb5634899d3`、
`31584a10f703f113f361bb1d88e0d8eaa5d927437ae8424d361247f72ca662bd`、
`7d3d6f08f2f73a0fe09639a76c5dde3c9b239ec11bd32b3113a45f85afb53d91`。

test-first 的 1.05 s authority-binding delay 在旧路径稳定形成 deadline miss，修复后通过；mapping mismatch、
post-verify exception、timestamp/identity/digest/cache/reuse tamper 与 per-child sampler isolation 均有负向覆盖。
focused 为 `61 passed`；真实 fast-child/preloader 与 no-exit probes 为 `2 passed`，0 loader/solver/result writes；
current-state broad 保留全部 v7 tests 与 v4/v7 fast probes，仅精确 deselect 9 个失效历史前提，结果为
`403 passed, 9 deselected`。Ruff 通过；canonical validate-only self/live=`13/193`、0 worker/loader/solver/write；
negative execute 因 future v7 PASS receipt absent 在 pre-import gate exit 1。v7 production lease 仍 fresh/unconsumed、
未读取；所有新 roots absent。本轮未运行 pilot/formal。当前仅 `READY_FOR_INDEPENDENT_REVIEW`，不是 PASS 或执行许可；
`execution_ready=false`、`pilot_executed=false`、`post_result_independent_review_passed=false`、
`formal_execution_ready=false`、`claim=false`、`security_certified=false`。

## 2026-09-01 Vnext v4 REWORK 与 v5 deadline-journal 后继

独立 reviewer `/root/pilot_post_result_review` 对 v4 的正式 verdict 为 `REWORK`。machine workflow receipt
`configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_review_rework_v4.json`（SHA-256
`975131dac0792b7f7b3016d7600b2aec0cba866214a5ab0b4e0e5f5300dd95c4`）与 non-authoritative evidence
`configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_review_evidence_rework_v4.json`（SHA-256
`e54c94a182ebe809ef773445f6b108290bd6cf33483c1136f71e2b9a2cf1080d`）精确绑定 v4 outer/inner/public anchor；
它们不宣称 reviewer cryptographic signature，也不授予 execution authority。唯一 blocker 是 deadline miss 在后续
slot 发生时，冻结的 exact-owned termination 最多需要 terminate wait `1 s` + kill wait `1 s`，而 v4 validator
对所有状态无条件使用 last-sample→exit `<=6 s`，导致约 `7 s` 的诚实 deadline-miss 路径被拒绝并丢失
`ResourceMonitorState.outcome`。此前 100 s gap、2 s catch-up、missing/lateness 与 lease cleanup findings 已通过本次复审。

v4 fresh lease 从未获授权或用于签名，已在不读取 seed 的条件下撤销。revocation receipt SHA-256 为
`dbf0c918dd29478935ece8300dc9b910505712e481b7b211dbbe4e2903a54cb3`，无 seed tombstone SHA-256 为
`be6b150c0dfd42fb1641680b0c6cf7e60e7ca3712d3f3cd2028034aa157da3b5`；v4 fresh/raw-consumed seed 路径均不存在，
v4 bundle、code 与 public anchor 原字节不变。

versioned v5 只修复上述 deadline-journal 持久化缺口，不改变 scientific hook/config、fixed 0008→0009、fresh child、
no retry/resume/reorder/skip、HiGHS 1.15.1/4 threads、10/8/2 GiB 门或 5 s/1 s 调度合同。v5 将 sealed
exact-owned termination 的两段 `1 s` wait 冻结为 audit-only `owned_termination_grace_ns=2_000_000_000`，并绑定
source `experiments/run_rq2_public_grid_two_block_pilot_activation_transport_v4.py` SHA-256
`04bfb1ac4deb51e1708c1eb668317b26e4cf2f3af68c35f18b96fb79f3af78a3`。normal child exit 仍要求
last-sample→exit `<=6 s`；deadline/resource/watchdog termination outcome 上限为 `8 s`。deadline miss 不会伪造 sample：
必须精确记录唯一 missed slot、expected/actual/unobserved due counts，以及 termination request/end wall+monotonic time、
duration、action、exact PID/create-time、2 s cap、sealed source 和 completion/failure state。0/1/2 s termination 返回可验证的
`resource_sample_deadline_missed` honest journal；`2 s + 1 ns`、identity/termination failure 或无法确认的 exit window
返回完整 `termination_indeterminate` evidence，均不推断 mathematical infeasibility。controller 在 incomplete status gate
之前 atomic 写入并 stable-read `controller_resource_journal.json`；同一完整 journal 仍可进入 receipt/ACK/accepted evidence/
controller receipt/result/success substantive mapping 与 Lamport signature。

v5 public anchor SHA-256/key id/commitment 为
`be3384bd8b40068e0b9aa81333617e93ca9bd96102fd9b9d51269345ca17ddf6`、
`96c07d7bbde974606a3b097e7de499b5a8a5aeee9df2dd88ac121afa39ed613b`、
`8344976a4758b431c091a0170f194803085fbf247e40fb352021ca3650d6a9d5`。production lease 仍为 fresh/unconsumed，
普通 import/API 无 production signing authority；`same_os_user_pre_execution_lease_exfiltration_out_of_scope=true`、
`security_certified=false`。

v5 config/contract/controller/worker/bootstrap/tests/inner/outer SHA-256 分别为
`f3bc07f63dba87ad5d541683c0250c04329f12d0d3d2f8a0f1e5664f1ed4b8bc`、
`dd9a6dba2ac826f988e5a16ccccd3e4f983ee6aa5b89de14b5aea8fd031b1ae4`、
`d8ac8e57fbb8d48ec730ff97801696bec678d16a9d470ec307f5b88182a18b72`、
`4a76ed133b5c04f9e8e3ea4bbe08393c8979d838f37564d71939581caab87769`、
`99e5f41a93fdc61ac057637abd7c25b5a843c890eefdd72d12823559ab7ef8d5`、
`a257c83469f2e10e94d469bff992f18912978cdcddee2906698a7499b89e2814`、
`e9c5cb678e15dadf6ee883879e4488c16dd59a813d94b87d09e8fe22ddb29447`、
`83ea9528f0f8f87bbc438a453c8365c97920a089161901692f4978591d5d8f20`。focused `64 passed`。10-file broad 首轮如实为
`375 passed, 9 failed`：其中 5 项仍假定 v2 PASS/result 不存在，2 项仍假定 v3 fresh lease 存在，1 项仍假定 v4
fresh lease 存在，均与当前已封存历史状态冲突；另 1 项 v4 fast probe 是瞬时首样本调度失败，单独复跑为
`1 passed`。明确 deselect 前述 8 项失效历史前提后，current-state broad 为 `376 passed, 8 deselected`，并保留且通过
v4/v5 fast probes。Ruff 通过；canonical self/live inventories 为 `13/168`，0 worker/loader/solver/result write，future
v5 PASS receipt absent，fresh lease present、consumed absent。当前唯一门是新的独立 v5 pre-run review 与 authority receipt；未运行 pilot/formal，
`execution_ready=false`、`pilot_executed=false`、`post_result_independent_review_passed=false`、
`formal_execution_ready=false`、`claim=false`、`security_certified=false`。状态仅
`READY_FOR_INDEPENDENT_REVIEW`。

> Current-state update（2026-09-01）：v5 已正式 `ESCALATE`；v6 完成 deadline/no-exit persistence 后又因
> broad-load 首样本 callback 内重哈希 authority closure 而关闭。当前唯一候选是 sealed v7（outer
> `7d3d6f08f2f73a0fe09639a76c5dde3c9b239ec11bd32b3113a45f85afb53d91`），其完整登记见上文 v7
> sampler-prebinding 后继段。v7 仅 `READY_FOR_INDEPENDENT_REVIEW`，PASS absent、lease fresh/unconsumed，未运行
> pilot/formal；execution/post-result/formal/result/claim/security gates 全部为 false。

## 2026-09-01 Vnext v7 ESCALATE 与 v8 due-slot priority 后继

v7 的独立 R4 verdict 为 `ESCALATE`。authority receipt/evidence SHA-256 分别为
`256f13db2a33c0a344b09230a7784a319b4bb20f8095c8bab2b44ae498b116d6`、
`06f4d1b496a8478fae12e5f17baeabe47f0b001e2654e76946c877f3a2ebee7b`。唯一 blocker 是
`monitor_owned_child_resources_journal()` 在读取 `now` 后先执行 child `poll()`，后检查 watchdog 与 current
scheduled/deadline；独立反例在 `now=1006000000001 ns`、首样本已成功且 child 已退出时得到
`persist_calls=0`、`state.outcome=null`。这不能证明资源门失败或数学不可行，只证明 v7 无法提供要求的完整审计证据。
v7 key 从未授权或用于签名，已在不读取 seed 下撤销；revocation/tombstone SHA-256 为
`0bf70cd3c24b716c124387af3427e3df76262c643e20a79a64e13bc390294f48`、
`da15732f4c9612bdb18edafff1460cdbcb968064c14178e18af4e9e3dd42d9bb`。

v8 是新的 versioned successor，不修改 v7 或更早 sealed bytes。loop priority 固定为：读取 `now`；先处理
`now >= watchdog_deadline`；计算 current slot/deadline；仅在 `now < scheduled` 时允许 clean-exit poll；
`now > sample_deadline` 必须形成唯一 missed-slot deadline evidence；inclusive window 内必须尝试 exact
PID/create-time same-pair sample。任何 incomplete outcome 仍须先 validate、atomic persist 与 stable readback，
再写入 state/resolve future，且 `mathematical_infeasibility_inferred=false`。fixed 0008→0009、fresh child、no
retry/resume/reorder/skip、HiGHS 1.15.1/4 threads、10/8/2 GiB、5 s interval、1 s jitter、1 s detection
overrun、2 s termination grace 与 21600 s watchdog 均未改变。

v8 config/contract/controller/worker/bootstrap/tests SHA-256 依次为
`d82bcd94d1554000b3d7db6b500c6b348fc90f7237bec53394c4ac3564258ac6`、
`fd77fb4acaa8cb519524883fbb2949d4d51f83a7a7778831ad43efa977e618cb`、
`b31fd4b221cc0a08a19f14a4387b2d59687260244ed529d2f2d68cf04fb85bb7`、
`5d399d0afc838a90809fa170639d75a8124d3a47297ddddd83714cd54b436c18`、
`74b3ea646d1774cfad5ddb87559e65de718217731160c51174cef5c9d56bf2d6`、
`3964249e8b3104915b0cea55116c6dfba52144178f8d2f619e7b72b4b46c00a4`；inner/outer 为
`2a4349242e6abea436816fae9fe0a2f482e58f881a682ab370b7a8ab2971f88c`、
`7090d339bc395fb714798ca8d96063943ef68113ab46091cdfe503c163a900d7`。public anchor/key id/commitment 为
`115bcc7bc7849a53c66331c6434bde1cfc4b426668b715488d4856a0f6df6dbd`、
`ec4ce96017b28b54216babf57615b78f9ce629b861ee2788f6667289ce9cce71`、
`7d84fbdc1836efe17ea7edcedc0b4fe8546d4769615c3bbd579f1d6c0ab5f180`。

test-first 在 sealed v7 上为 `1 passed, 4 failed`，四个 failure 精确复现 due/deadline/watchdog poll bypass；v8
同组为 `5 passed`，full focused 为 `66 passed`。真实 fast probe 为 sample/expected `1/1` 且
`start <= first <= release < exit`、0 loader/solver/result write；no-exit probe 为
`resource_sample_deadline_missed`、atomic readback true、0 loader/solver/result/success write；preloader 也是 0
loader/solver/result write。Ruff 与 canonical validate-only 通过，self/live inventories 为 `14/206`；negative
execute 因 future v8 PASS absent 在 pre-import gate exit 1。

broad 账目完整保留：raw `479 passed, 13 failed`；13 项均为已失效的历史 state assertion 或 superseded sealed
V5/V6 broad-load resource regression，无 v8 failure。精确 deselect 该 13 项后的首轮为
`478 passed, 1 failed, 13 deselected`，唯一红点是必须保留的 sealed v4 fast probe；该 node 单独复跑
`1 passed`。在无残留 pytest/worker 后以相同命令第二轮为 `479 passed, 13 deselected`，并保留通过 v4/v7/v8
fast probes 与全部 v8 tests。不得把首轮写成 green，也不得据此改写 sealed v4–v7。

独立 reviewer 明确以同一 11-file/13-deselect 命令复跑，结果为 `478 passed, 1 failed, 13 deselected`，同一
sealed v4 fast node 隔离连续两次失败；reviewer 未提供隔离执行的 exact argv/stdout，也未提供失败时
ResourceMonitorState、journal、phase/counts/timestamps/overrun/termination 或 child returncode。外部只读 runtime
instrumentation 在不修改 v4 code/test 的一次复现中返回 `child_exited`，sample/expected=`1/1`、returncode=0、
loader/solver/result write=`0/0/0`，未复现失败；sample lateness 为 `969000000 ns`，完整成功 journal SHA-256 为
`0d62844b8e02f763018b85ea200c168492bd8526fe6042a9016a7c845dfb1555`。非权威 machine evidence 路径为
`configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_v4_sealed_superseded_fast_probe_regression_evidence_v1.json`，
SHA-256 为 `e2138fd2038a6d330149e05e01507618f646bd5a9c5f4d60e026507242f16111`，`authority=false`，且不属于 v8 bundle。
由于 reviewer 失败路径缺少可核验 journal，本记录不猜测失败 phase/root cause；结论仅为当前 v4 failure 不可复现，
v4 已 sealed/superseded，不构成 v8 finding。将该 v4 fast node 精确增加为第 14 个历史 deselect 后，原 11-file
current-state broad 为 `478 passed, 14 deselected in 348.20s`，保留并通过 v7/v8 fast probes 与全部 66 个 v8 tests。

当前状态仅 `READY_FOR_INDEPENDENT_REVIEW`。v8 production lease fresh/unconsumed 且未读取，future PASS receipt
与 result/worker/success/terminal/log roots 均不存在；未启动 pilot/formal。execution/post-result/formal/result/
claim/security gates 全部为 false；下一步只能是独立 R4 pre-run review。

## 2026-09-01 Vnext v8 nonformal evidence run（post-result review pending）

独立 pre-run review 只授权外置 execution-review receipt 与一次 nonformal 运行。receipt SHA-256 为
`04cd6b421ebeef07e00c1d8ab08bb15d721110ff454c32e7898eca2eff6b486e`，精确绑定 v8 outer
`7090d339bc395fb714798ca8d96063943ef68113ab46091cdfe503c163a900d7`。启动前同一 preflight 的 self/live
inventory 为 `14/206`；5 个 v8 roots 与 3 个 protected roots absent，related process 为 0，formal runner/config
及 9 个 checkpoints 精确；production lease 只检查了 462-byte metadata、mtime 与 owner-only ACL，启动前未读取内容。

关于本次 preflight resource gate，`15,472,906,240 bytes` 及任何相关观测时窗仅是
`non-authoritative executor telemetry`；仓库中没有对应的 machine-readable/signed artifact，独立 reviewer
不能验证该 exact value/time。唯一可认证口径是：sealed V8 runner 在 lease consume 与 worker spawn 前调用
preflight；本次 execution 已 committed，证明该调用未抛错，因此只能机械证明
`threshold_passed: available commit >= 10 GiB`。后续 resource journals 只记录运行期 samples，不能倒推
preflight exact observation。不得为本次历史 preflight 补造 timestamp/receipt，也不得重跑 one-shot V8。

future formal activation successor 的验收合同冻结为：必须在 formal spawn 前、lease/activation consume 前（若有）
对当时的 preflight machine evidence 做 atomic persist + stable readback；字段至少包含 `wall_time_ns`、
`monotonic_ns`、`observed_available_commit_bytes`、`preflight_threshold_bytes = 10 GiB`、
`child_private_commit_stop_bytes = 8 GiB`、`system_commit_available_stop_bytes = 2 GiB`、authority
mapping/binding digest，以及 threshold comparison/result。该 artifact 必须进入 activation authority/receipt，
并在任何 formal spawn 前验证。

唯一 run 的 controller PID 为 `29036`，session 为
`9d16ff4da3bab583876d6fbf5d09c0dde4bc5b3bc57334b891cfe38038044f62`。0008 worker PID/create-time 为
`30404/13432731802848210300`，record digest 为
`ef04c57b9e3054f157b0f1bd5b76e0324da6776890588ab574165feb7692169c`；0009 为
`8600/13432731839688457900`，其 predecessor 精确等于该 digest，最终 record digest 为
`52a96c22f164afbbe34916d86f86c3dd1daa58cb5c66a0ea3a019fc1e123d6a8`。两 block 均为 24/24 hours resolved、
exogenous grid infeasibility count 0、observed `grid_need_mw=0`；solver-call accounting 分别为
`1 baseline + 2 primary = 3` 与 `1 baseline + 24 primary = 25`，实际 runtime 为 HiGHS 1.15.1、threads=4。
这只是本次 nonformal evidence payload 的机械记录，不是 full-N-1、AC、正式方法或工程安全结论。

两份 resource journal 均为 `child_exited`、mapping pre/post digest exact match、无 deadline miss/termination、
`mathematical_infeasibility_inferred=false`。0008 sample/expected=`6/6`、maximum private commit
`552194048 bytes`、minimum available commit `14947889152 bytes`、last-sample-to-exit `1.812 s`；0009 为
`39/39`、`629366784 bytes`、`14744317952 bytes`、`4.219 s`。全部 sample lateness 为 0，相邻 gap 精确 5 s。

public-only `verify_published_artifacts()` 将 publication 分类为 `committed_success`。result/PUBLISHED typed-tree
file SHA-256 为 `03528f052f127d819dc07edff860efd7652e5b28da34cfac6be245ba0e75331c`、
`f01ec3391a20d692aa8974c08da8f1af81dd4b79a07e1aff9cb0290fea4f8920`；result manifest/controller receipt/
attestation/success SHA-256 为 `99f56a6809f25eb0bf2916b84d76bd821513f6ce6d8ff7d6ddd53c3e9cf81af4`、
`07313f039b443ba795f1f6c8ee127d9aa4467df0db1cc9f41f7d7308b59d9b5f`、
`fcad55dd407c5725815ec4b6047833331f0424525129eb0288cf77bdea1ca53b`、
`957f5e759e6c4ba71d26a5a18b37b9ef8f3935005f8b09c545b73ec7dcb0c604`；Lamport payload/signature SHA-256 为
`158b14130823a80acfa643c2df7ab7611ad518ed7c1647864501c3ab719eecda`、
`0a595309844822ba529db6e1a5c7d8ddf2f47ef60fc7a130dd8014e01b347c7f`。fresh/raw-consumed seed 均 absent，
只保留 SHA-256 `8e5f25e1b8a3aecb4d2a32a2a6d55aea65ca178425e6d47e9cf9fec35d378aa2` 的 no-seed/nonreusable
tombstone；TERMINAL absent、related process=0，formal runner/config/9 checkpoints post-hash unchanged。

当前状态为 `post_result_review_pending`，不是 post-result PASS。formal 未启动；
`post_result_independent_review_passed=false`、`formal_execution_ready=false`、`formal_result_exists=false`、
`claim=false`、`security_certified=false`。下一步只能由独立 R4 reviewer 审查本次 sealed result/PUBLISHED evidence。

## 2026-09-01 V8 post-result PASS 与 formal activation successor v1（待独立 activation review）

独立 post-result reviewer 的最终 verdict 为 `PASS`、`findings=[]`；machine-readable external receipt
`configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_post_result_review_pass_v8.json` 的 SHA-256 为
`28e546b8f5f3bc8c8402c86ec723ec9e35da041ba74676c9adb59cd338980ca6`。它精确绑定 V8 outer、pre-run PASS、
result/PUBLISHED trees、success、controller receipt/attestation、Lamport payload/signature、无 seed tombstone与冻结
formal artifacts，并明确 `materialized_from_review_report=true`、
`cryptographic_reviewer_signature_present=false`。该 verdict 只关闭 V8 post-result evidence gate，不把 nonformal
pilot 升级为 formal/result/claim/security evidence。

新的 versioned formal activation successor v1 从 block zero 启动，禁止 Gurobi/HiGHS predecessor checkpoint
reuse、resume 或 retry，使用全新 checkpoint/worker/log/output roots。它保留 1071-block science hook、HiGHS
1.15.1/4 threads、10/8/2 GiB、5 s exact slot、1 s jitter/overrun、2 s termination grace 与 21600 s per-block
watchdog；每个 worker 的完整 V8 resource journal、actual solver runtime evidence 与 execution receipt 原子进入
checkpoint。formal spawn 前必须先把当前 Windows available system commit 与 wall/monotonic time、三项冻结阈值、
authority mapping/digest 和 comparison/result 原子持久化并 stable readback；不足 10 GiB 时不 consume authority、
不 spawn、也不创建四个 formal roots。

successor inner/outer SHA-256 为
`5e4eba6b7bc4ca7364725bbe73f4d7db4ba2e290ec413035ed4e5e5957cb204c`、
`b492e4babe182d38ad6be865df424d1cce59cef57c2c6a85b896cffddfad0b87`。focused 为 `11 passed`；raw related
`74 passed, 3 failed` 的三个红点均为 V8 已完成后失效的 pre-run receipt/lease/root-absence 历史断言，精确
deselect 后为 `74 passed, 3 deselected`。Ruff、compile、bootstrap/controller validate-only 均通过且为 0
solver/0 formal-root write；negative execute 在外部 activation PASS
缺席时于 preflight/consume/spawn 前拒绝。当前 one-shot authority 仍 fresh/unconsumed，activation PASS receipt 与四个
formal roots 均 absent。唯一剩余门是独立 formal activation review；状态仅
`READY_FOR_INDEPENDENT_FORMAL_ACTIVATION_REVIEW`，formal/result/claim/security 全部为 false。

## 2026-09-01 formal activation v1 REWORK 与 startup-handshake successor v2

独立 reviewer 对 v1 的正式 verdict 为 `REWORK`。exact finding 是后台 formal controller 启动证据不足：v1
Popen 后未取得和持续验证 exact PID/create-time，也没有 controller authority-accepted startup handshake，因此
immediate exit 仍可能生成 `formal_controller_spawned=true`。machine receipt
`configs/rq2_public_grid_highs_formal_activation_successor_review_rework_v1.json` SHA-256 为
`bb398d74c67fdfce41d7fcc64e58820a5f8ad6f16d3ba1ff5c9e1a7d529b6a14`，明确无 reviewer cryptographic
signature，且 v2 写权限来自 active user objective 与 `agent.md` §7 唯一 REWORK，不冒充 reviewer PASS。v1
inner/outer/code/config/test/lease 全部保持原字节，v1 activation/execution authority 为 false。

v2 只修 startup identity/handshake，不改 science hook、1071 blocks、HiGHS 1.15.1/4 threads、10/8/2 GiB、
5 s/1 s/1 s/2 s/21600 s 或 publication semantics。Popen 后 bootstrap 立即取得 controller PID/create-time；任何
poll/handshake/READY/release 检查都重验同一 pair。controller 在 dynamic authority、consumed tombstone、exact
cwd/env/Python、authority mapping 和 clean roots 全部通过后，且在 science hook/solver/formal-root creation 前，
atomic persist + stable readback handshake，绑定 controller/bootstrap pairs、formal config/controller/outer/dynamic/
preflight/activation receipt/consumed authority hashes、exact command/cwd/environment。controller 等 bootstrap ACK，
再写 READY 并等 science release；bootstrap 只有验证 READY 与 live exact pair 后才可写 release 和 spawned=true。

handshake 前 exit/timeout、PID reuse/create-time drift、malformed/tampered evidence 都写 machine-readable
`launch_incomplete`，其中 spawned/formal_started/result/claim/security=false、no retry/no resume、不推断
mathematical infeasibility；仍存活的 exact-owned child 使用 PID/create-time 安全终止，identity 不确定时不向可能复用
PID 发信号。v2 config/formal config/REWORK receipt/contract/controller/bootstrap/test/inner/outer SHA-256 为
`5e9c612bb295305f1119b23552e6ae1c946ad8d00bda03e48927f971c93e4a46`、
`42fe57202b56d9f628f81576ea2b115159d7418a4ff68911fce452e26898aef4`、
`bb398d74c67fdfce41d7fcc64e58820a5f8ad6f16d3ba1ff5c9e1a7d529b6a14`、
`8201bf2333649100cf8a57f8f1d90b39da575670cf7621bd374a4bd98d7bc007`、
`98ee752cedcbac8b05f44614bc1cf7a9aae5d757c36c569bbcde0a51ee2664c0`、
`08977267e12bb4c59630225bf8452d3fb8f1883664c14b154bb176a018387654`、
`ab4f0e7b4bc5ee79f86a4de142bcbd0f3a8f05bf7cc229397d373ec59dbdd3ad`、
`ef1812d0b48426770e7137f668fbb64e6f4a7fe04f220e9d726fc10c37cc1e0d`、
`8c5db5e265141378b537e9e3096198c0f86221a324423a646d6645d107b56764`。

test-first missing v2 module 为 red；focused `7 passed`，related current-state `81 passed, 3 deselected`，Ruff、
compile、bootstrap/controller validate-only 均通过且 0 solver/0 formal-root writes。v2 review PASS、consumed lease、
activation audit root、四个 formal roots及相关 process均 absent。当前仅
`READY_FOR_INDEPENDENT_FORMAL_ACTIVATION_REVIEW`；formal/result/claim/security 全部 false。

## 2026-09-01 formal activation v2 ESCALATE 与 successor v3 双门禁

v2 独立 R4 verdict 为 `ESCALATE`。receipt
`configs/rq2_public_grid_highs_formal_activation_successor_review_escalate_v2.json` SHA-256 为
`e80c4bb85a977e6819b5ceb259761e6c1be642c12d37f83020772a569805f54c`，绑定 v2 outer
`8c5db5e265141378b537e9e3096198c0f86221a324423a646d6645d107b56764`，明确来自 reviewer report、无 reviewer
cryptographic signature、无 execution authority。重复验收失败包括 reviewer PASS/user run authority 未分离、实际执行
import closure 未由 frozen expected hashes 封口、release 后失败状态不诚实，以及缺真实四阶段 E2E/失败矩阵。v2 全部
sealed bytes、fresh lease 与 absent roots保持不变。

用户只授权 `sol_modeler` 设计新的 versioned successor；该指令不是 formal-run authority，未被写成任何 run-authority
receipt。v3 固定两条串联外部门：future review PASS effect 必须保持 `formal_execution_authorized=false`；future explicit
user formal-run authority 必须另行绑定 exact outer/review/formal config/controller command/50-file closure/one-shot lease。
后者 absent 时 bootstrap 必须在 preflight、consume、spawn 和 activation-audit-root write 前首先拒绝。

v3 当时登记的 50-file execution closure 完整性已被独立 R4 review 否定。其 `ast.ImportFrom` resolver 不理解
`node.level`/source package，因而漏掉 package initializer 实际导入的 local modules；至少包括 `ac_validation`、
`network_grid_need`、`scopf`、`service_risk`、`osqp_qp`。V3 manifest 的 frozen expected hash 只能覆盖这个不完整集合，
不能作为 actual execution closure 完整性的证据。

V3 虽区分 release 前后 outcome，但 bootstrap 在 acceptance/spawn receipt 后即返回，不能监督完整 block lifecycle；
acceptance 后 `os._exit`/kill 可绕开 controller self-report，且 controller/bootstrap 双写使用 overwrite-capable primitive。
因此 V3 post-release closure 也未成立。1071 blocks、block zero、HiGHS 1.15.1/4 threads、10/8/2 GiB、
5/1/1/2/21600 s 与 science/claim/security semantics 本身未改变。

v3 closure/inner/outer SHA-256 为
`cdc272b2f98d637c4ed020d4303c35ba29ed3e5c3c38994ece722509751f44e2`、
`cf05fcf2c05a42b4b5cfb36c535fd7b54fc2dac69f2ebbbdc76f220f42971f51`、
`087127892db1a55955ddc87b2491520a61a9b19d6d7f0e56040ce0c9d980ee3b`。focused `10 passed`；V1/V2/V3
`28 passed`；related current-state `91 passed, 3 deselected`。transport broad 首轮
`137 passed, 2 failed, 3 deselected`，两项 live preloader 是当时 available commit 未达冻结 10 GiB 的正确 fail-closed
结果，未写正式 preflight evidence；精确 deselect 后 `137 passed, 5 deselected`。Ruff、AST、两个 validate-only 通过，
0 solver/0 formal-root writes。negative execute 首先因 user authority absent 拒绝，fresh lease hash不变，consumed/audit/
formal roots absent。

V3 independent verdict 为 `ESCALATE`，故 `independent_v3_activation_review_passed=false` 是历史失败事实，不再是待满足
gate；V3 不得创建 PASS 或继续启动。V3 fresh lease仍 unconsumed，formal/solver process=0、formal/result/claim/security=false。

## 2026-09-01 formal activation v3 ESCALATE 与 V4 review gate

V3 independent review receipt
`configs/rq2_public_grid_highs_formal_activation_successor_review_escalate_v3.json` SHA-256 为
`7c6afdfbd3eb7746ed8851162852c074f10d48ac117894c22a8d5487266d9c1c`，绑定 V3 outer
`087127892db1a55955ddc87b2491520a61a9b19d6d7f0e56040ce0c9d980ee3b`。两个 critical blockers 是：

1. V3 relative-import resolver 导致 actual local execution closure 不完整；
2. V3 protected window 未覆盖 release acceptance 后的完整 controller lifecycle 与 immutable dual-writer evidence。

V4 versioned successor 已以 77-file frozen expected-hash manifest闭合第一个 implementation finding。production AST
resolver 实现 package-relative semantics，并只允许三处 sealed computed dynamic import sites；独立 stdlib
`modulefinder` bytecode oracle（不复用 production helper）得到 exact 同集。V4 controller/bootstrap 以 immutable
create-if-absent machine artifact 和持续 exact PID/create-time supervision 尝试闭合第二个 finding，但独立 review 证明
该 closure 不成立：release persist→acceptance wait 的首个 bootstrap `try` 只捕获 `Exception`，漏掉
`KeyboardInterrupt`/`SystemExit`；terminal-success 与 unresolved writers也没有共享的跨终态互斥。per-file hard-link
create-if-absent 不能阻止两个不同 terminal artifacts 同时存在。

V4 focused 为 `15 passed`；包含 closure oracle/drift、真实四阶段 PID/create-time、ACK/READY tamper、production
spawn-receipt persistence failure、post-acceptance `os._exit`、block-0 injected exception、root observation、normal terminal
success及 pre-release classification。V4 outer 为
`6936d06a5bc8d191f5eaf235fe7784c36193ac6343d88d16cbbd3e5bea8d2068`。当前 V4 review PASS 与 explicit user
formal-run authority 都 absent，V4 lease fresh/unconsumed；本轮用户指令仅是 design authority。formal roots/audit root absent，
formal/solver process=0，formal/result/claim/security=false。

V1–V4 为 `43 passed`；related raw/current-state 为 `106 passed, 3 failed` / `106 passed, 3 deselected`；transport broad
raw/current-state 为 `154 passed, 3 failed` / `154 passed, 3 deselected`。三个 raw failure 均属于 sealed V8 已运行后失效的
absent-state assertions；本次两项 live preloader tests 均通过，不存在 V4 implementation/science regression。

V4 independent R4 verdict 为 `ESCALATE`。machine receipt
`configs/rq2_public_grid_highs_formal_activation_successor_review_escalate_v4.json` SHA-256 为
`1d4f5f1b65512a0092438051055171c5abf4dbbe2aa358675c5f580636bc4e9c`，绑定 exact V4 outer、reviewer
`/root/v4_activation_review`、两个 critical finding与一个 major test gap，无 cryptographic reviewer signature、无 execution
authority。reviewer fault injection 明确观察到 release persisted、unresolved absent、child still live；另一 critical 是同一
attempt 可同时出现 terminal success 与 unresolved。77-file closure/oracle本次无新 blocker，但不能抵消 post-release gate
再次失败。

V4 已成为历史 `ESCALATE` candidate，不得创建 PASS、user run authority或运行。当前没有可启动 formal candidate。下一步
必须由用户明确授权新的 versioned successor（V5）；此前 V4 design authorization不授权 V5，也不授权 formal run。V1–V4
sealed bytes保持不变，PASS/user/consumed/audit/formal roots absent，fresh lease未消费，formal/solver process=0，formal/result/
claim/security=false。
