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
| M6完整网络-业务时序闭环 | V6 official `ESCALATE`; V7 development evidence partial, Windows/PRE_SEAL pending | v5的202个HiGHS checkpoint仅作诊断，Gurobi正式attempt仅保留9/1071个历史checkpoint；HiGHS V8 nonformal `0008 -> 0009`已有post-result review。V7已补前序ESCALATE receipt的sealed-inner绑定；开发机新增18个完整临时封存快照用例，真实校验器串联到spawn边界，连同6个相邻回归为`24 passed in 100.18s`。其中有效反例发现lease已reserved时仍先创建activation目录，已在同一draft把preflight authority校验移至目录分配之前。当前收集101项；macOS证据不覆盖Windows原生consume、实际controller握手/终态和全量回归，原83项通过记录是历史字节证据。未物化仓库production artifacts或启动正式运行 | 完成Windows当前矩阵与fresh独立PRE_SEAL审查前，writer evidence complete、sealed-ready及formal/result/claim/security全部保持false；完整grid发布前pairwise/identification保持关闭 |
| RQ2 HiGHS同进程thread scheduler隔离 | mitigated for V8与V7 draft controller；PRE_SEAL remediation in progress | V8及V7 controller保持per-block fresh worker、1071 blocks、HiGHS 1.15.1、4 threads、PID/create-time、solver-call accounting和resource journal。当前V7补充的是生产授权链测试及preflight写入顺序修复；不改变solver、资源阈值、进程隔离或科学协议。开发机未启动solver，原双validate-only及83项full记录不代表整改后执行机验收 | 完成整改后的测试矩阵及fresh PRE_SEAL复核前不得seal或启动formal run。正式执行路径必须保持per-block process isolation，不得回退到同进程连续求解或把资源停止解释为不可行 |
| RQ2 Vnext two-block pilot post-result evidence | V8 nonformal `committed_success`; post-result `PASS` | v8唯一一次fixed `0008 -> 0009` run已发布result/PUBLISHED exact trees；public-only readback、fresh PID/predecessor、HiGHS runtime、resource journals和无seed tombstone均通过。独立post-result receipt SHA-256为`28e546b8f5f3bc8c8402c86ec723ec9e35da041ba74676c9adb59cd338980ca6` | 该PASS只关闭two-block evidence门，不形成formal result、论文claim或security certification。它是V6/V7绑定的前序证据；V6 official review已`ESCALATE`，V7仍为无执行权限的draft。先完成V7当前Windows验收矩阵，再交fresh PRE_SEAL review；不创建production artifacts、不启动formal run |
| RQ2四臂归因v1前序 | superseded for primary attribution; implementation-only | 四臂core、checkpoint/external-preflight与旧互斥identification/report合同已实现为validate-only；现有70-cell阴性结果和全部sealed bytes保持不变 | 旧exclusive classifier不作为联合前沿主结论authority；不得覆盖旧协议或用其启动新46-cell流程 |
| RQ2联合服务可交付前沿 | v5 independent R4 `PASS`; implementation v2 independent R3 `PASS`; execution v3 independent R3 `PASS` | 用户在v2 `ESCALATE`后明确授权v3；v3移除live receipt永久缺失假设，递归绑定v2/v1 authority并拒绝旧fixed PASS普通entry与dangling symlink。22-member outer为`b153f0320fe9dfe961575be4836f4bcf4044836be4fa66618119fc08d4cbce80`，official review及post-receipt stability均为`0/0/0` | independent review gate已关闭；dispatched-grid、Windows runtime、native replay、memory/transport、fresh-process activation及单独formal-run authority仍缺失，全部formal execution/result/claim门关闭 |
| RQ2联合服务24小时边界与training support | scientific-protocol blocked; continuous-boundary draft non-authoritative | 零solver审计发现sealed v5每个block强制hour 23 inactive/零债务，与hour 23正CFE必需请求结构冲突；冻结training中按alpha为358/478/541/541个power blocks触发。用户已选择continuous multi-day state carry；新增草案与边界组件仅验证状态/provenance延续 | 不改写sealed v5或既有review。必须先完成versioned continuous科学协议、continuation/deadline/accounting数据门、正式planner与fresh独立R4 review；不得用V7计算链或移除terminal条件直接打开46-cell planning/formal/result gate |
| 真实重大停电事件分布 | processed candidate cohorts; independent-event calibration blocked | 已冻结1534源行、1521候选组及主/敏感性队列；主持续队列1385组/1398源行，重复组保留source IDs并以非缺失max/min而非求和审计 | 候选组不证明独立物理事故，仍不得估计事故频次或无条件时长分布；无资产ID、拓扑和SCUC，不得映射为RTS具名N-1或声称与业务同钟 |
| Google同系统工作负荷-功率配对 | unfiltered full-month CPU-power-capacity alignment available; quality/population/model input blocked | 744小时每小时保留14个CPU strata、12个五分钟power样本均值/原flag计数和同钟capacity evidence；23小时诊断与原获取包仍保留 | 只关闭未过滤同钟数据对齐；不是quality-eligible功率、完整PDU人口、绝对MW、真实柔性或恢复证据，不能替换Alibaba或进入continuous/formal模型 |
| RQ2本地公开数据交付入口 | resolved for offline catalog/validation/loading scope only | 12个既有Google、Alibaba、RTS-GMLC、Zeus、NLR、WattGPU与continuation包由统一catalog、双轴field dictionary、input status和流式loader逐字节校验 | 只关闭本地软件交付与可读性；20项业务/恢复输入仍为null，6项科学协议未注册，`full_rq2_experiment_input_ready=false`、`formal_result=false` |
| ENTSO-E观测资产事故 | external-blocked on security token | 匿名API实测401，当前环境无令牌；页面批量导出同样要求登录 | 用户完成免费注册和REST API令牌申请前不执行；取得后仍不得把ENTSO资产ID映射为RTS ID |
| X只有MW上限 | mechanism-only | 新增连续轨迹包络，硬检查响应、持续时间、休息、事件数、MWh、债务、恢复功率和期末债务 | 合成参数不能解除合同认证阻塞 |
| T指标依赖声明的静态24小时 | resolved as evidence separation | 静态M3的连续验证小时改为0；另以8784小时时间轴输出显式压力轨迹里程碑 | 正式逐时运行T仍受时序电网和业务数据阻塞 |
| 50% Pmax响应与机组事故频率安全 | external-blocked | 继续标记合成灵敏度，机组持续事故不冒充响应前频率状态 | 不能签发运行安全或响应认证 |
| branch 10非计划孤岛 | external-blocked | 排除并作为失败单列；数学多岛平衡不视为处置证据 | 正式N-1认证受阻 |
| 扩建缺少AC工程参数 | external-blocked | 只报告DC MW机制结果 | 不能进行扩建AC认证或把MW增量写成MVA |
| 固定在线机组、无逐时新能源与跨时约束 | external-blocked on RTS-24 mapping | RTS-24仍只使用8784小时时间轴和Area 1负荷代理；独立原生RTS-GMLC已完成24小时benchmark | 原生24小时结果不能回填机组集合不同的RTS-24，也不能据此声称RTS-24逐时SCUC、可再生联合安全或运行认证 |
| PAI作业请求到绝对功率映射 | external-blocked for empirical MW claims; not required by dimensionless primary estimand | Alibaba已有job包络与生命周期遥测；NLR、WattGPU及新增Zeus受控DNN训练功率表提供外部硬件证据，但均不共享Alibaba job、模型与时钟；Zeus的Alibaba映射为作者构造而非观测链接 | `direct_job_to_power_mapping_ready=false`继续阻止Alibaba绝对MW与经验合同结论；外部GPU表只作尺度/机制检查，不能回填逐job绝对功率 |
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

#### 联合服务可交付前沿确认性设计门（2026-09-03）

新RQ2科学协议以四臂离散需求前沿为主：
`D_N`、`D_C`、`D_B`、`D_J`，并注册

`I_joint = D_J - max(D_N,D_C)`，
`I_sep = D_B - max(D_N,D_C)`，
`A_B6 = D_J - D_B`，
`I_joint = I_sep + A_B6`。

完整事件包络下不预设四臂容量顺序；加法分解是fail-closed结构门。确认性参数矩阵由36个
`hourly_cfe_target × flexible_fraction × normalized_recovery_headroom`
full-factorial cells和10个锚点OAT cells组成，共46个唯一cells。结果采用可并存
bottleneck vector，分别报告network/CFE single-service binding、joint extra
requirement/portfolio relief、B6 capacity under/overprovisioning和operational
penalty/relief。

v1科学配置`configs/rq2_joint_deliverability_preregistration_v1.yaml`已seal；
稳定回读发现v1执行方案第5节仍含一处与非嵌套口径冲突的旧验收措辞，因此v1
outer只作不可变前序，不作为当前review入口。v2语义修正successor
只替换该验收项，不改变研究问题、estimands、46 cells、阈值、solver contract或
执行权限。v2状态为`SEALED_READY_FOR_INDEPENDENT_REVIEW`，inner与outer
SHA-256分别为
`1e4140558baac410898822d101c9516e54e01a5026fd8535e18df3cf44778ec3`和
`ae1e8a8a5c4c276e5c0d54900636de94e5402f29923817cf8cb70067b90c90f7`。

target-specific完整CFE缺口与CFE-compatible recovery builder、46-cell
implementation、successor attribution payload、runner和output path均为null。
旧v6、四臂v1及其exclusive classifier保持原字节，只作为前序机制资产。

当前剩余设计门是由新`sol_reviewer`对exact outer签发独立R4 PASS；随后另建
versioned implementation successor并通过R3/R4 review。即使科学协议review通过，
完整grid package、单独user formal-run authority和execution readiness仍必须另行
满足。当前solver/formal/result/paper-claim/security门全部关闭。

#### 联合服务可交付前沿v3 R4 ESCALATE（2026-09-04）

v2 exact outer
`ae1e8a8a5c4c276e5c0d54900636de94e5402f29923817cf8cb70067b90c90f7`
的首次独立R4 verdict为`REWORK`，记录见
`configs/rq2_joint_deliverability_preregistration_review_rework_v2.yaml`。
聚焦v3 successor随后显式区分network-only业务恢复、CFE-compatible恢复和B6
grid/CFE双track恢复，增加alpha=1结构性undefined、solver证书区间传播、完整时序
常数、代表点算法、holdout状态机及E0条件分母。v3 inner/outer SHA-256分别为
`ae99e836bbaaa7a5c26674596e2600cfee94365b3ea8d4dd1cb2ec382425dd02`和
`edbbe5be9ae559a258b8928a6678e4adc9abeda4ce9c841238d67589d372bc99`；
定向继承测试为`40 passed`，Ruff和recursive hash检查通过，solver/result write均为0。

唯一复审的official verdict为`ESCALATE`，无Blocker但仍有4项Major：

1. v1的`frontier_outputs`与`attribution_contract`点值规则未被完整supersede，
   与v3 interval-supported符号规则冲突；
2. v3 validator对6类科学语义变异均未fail closed，硬编码
   `corrected_major_findings=5`不能证明闭环；
3. 结构性零恢复precheck只挂在alpha=1名下，未覆盖12个
   `normalized_recovery_headroom=0` primary cells及所有arm-track-cell；
4. bootstrap未冻结PRNG/version、ID顺序、random stream消费、加权抽样和percentile
   estimator，仍不能保证逐字节复现。

machine-readable ESCALATE receipt为
`configs/rq2_joint_deliverability_preregistration_review_escalate_v3.yaml`，
SHA-256为
`0e0acf0ddf49d2eca3c68529b3cf111eb90f0cdda6d7c6ce6bbf6421d2d533d3`。
v3 sealed bytes保持不变，状态为historical escalated candidate。
`independent_R4_review_passed=false`、`implementation_bound=false`、
`formal_execution_ready=false`、`formal_result=false`、`paper_claim=false`。
只有用户明确授权新的versioned scientific successor，才能继续修复；此前不得
开发46-cell implementation、运行solver或生成结果。

#### 联合服务可交付前沿v4 REWORK与v5 PASS（2026-09-05）

v4以完整、自包含协议关闭v3的4项Major，inner/outer SHA-256分别为
`830507026508d051592861c9010142d1cf8a9823638fbb71b0066dba594653c5`和
`101fc1bc071b06779ee779beb1bb7b5f61640af8fa4b8ccb7f44b7c019710a3e`。
独立R4 verdict为`REWORK`：v4将scalar transport endpoint的全称量词与
common-\(\pi\) compatibility的存在量词混用于operational attribution。
machine-readable receipt为
`configs/rq2_joint_deliverability_preregistration_review_rework_v4.yaml`，
SHA-256为
`dab9573ed70689edbf64408c2b690f7016520839c706e2592cf5177ef7bad954`。
v4字节保持不可变，未取得implementation或execution权限。

聚焦v5封口后的config SHA-256为
`19d61a2913e346090db23d01de587b650d8599999c40a78a291f627915ec2a69`，
semantic payload SHA-256为
`31be646a725f9aef7498fd57b140b404828bfba4afa9c98912c20346aae4b8e4`。
v5把operational label量词唯一冻结为
`exists_registered_metric_then_for_all_admissible_pi`：penalty只在至少一个
metric的certified scalar lower endpoint严格大于`1e-6`时成立，relief只在至少
一个metric的certified scalar upper endpoint严格小于`-1e-6`时成立；
existential common-\(\pi\) witness不进入label或claim。
四臂点值恒等式继续固定为`I_joint=I_sep+A_B6`，但所有符号标签只读取证书区间。

v5 pre-seal审计发现的登记不同步已由本节和状态总表闭合；严格阈值的4个
`nextafter`边界测试也已补齐。当前focused tests为`36 passed`，v1-v5相关回归为
`111 passed`，Ruff check/format通过，validator报告0 solver call、0 result write。
v5 inner/outer SHA-256分别为
`84847114b6cd66925326f541f2ecfbd0ad825ca0591d09894c51c2db2ac1162f`和
`92a58498e1de5f84b132067e3d4a4443ae841747846785e9df54cd9afd7efdfd`，
状态为`SEALED_READY_FOR_INDEPENDENT_REVIEW`。全新独立reviewer对exact outer的
official verdict为`PASS`，`Blocker/Major/Minor=0/0/0`。machine-readable receipt为
`configs/rq2_joint_deliverability_preregistration_review_pass_v5.yaml`，SHA-256为
`0ec073c38eac003255fa2d2753edb28f4d02e0f7756c34e185027ac23b140722`。
该PASS只关闭scientific preregistration review gate；不授权implementation、solver或
formal run。implementation successor和formal run均需用户另行明确授权。

#### 联合服务可交付前沿 implementation successor v1（2026-09-05）

用户已授权 V5 reference implementation、pre-seal audit、seal 和独立 R3 review，
但未授权正式求解。v1 已封存为 `SEALED_READY_FOR_INDEPENDENT_REVIEW`，实现文件为
`src/models/rq2_joint_deliverability.py`、
`src/scenarios/rq2_joint_deliverability.py`、
`src/evaluation/rq2_joint_deliverability.py` 和
`experiments/run_rq2_joint_deliverability_implementation_v1.py`。

已闭合的实现语义包括：exact 46-cell inventory、target-specific完整CFE缺口、
四臂track-specific recovery、全training support结构门、network-only alpha复用、
certified capacity interval、有符号归因、current-state holdout、E0 conditioning、
scalar transport、PCG64DXSM bootstrap和nonformal typed-tree publication。
pre-seal审计发现的 identification cell 顺序冲突已改为全链使用注册顺序，并由
finite `runner -> output validator`端到端测试覆盖；raw/effective请求混用、
非training E0绕过、full-support状态绕过、proven-infeasible残留数值字段和
solver-options自报阈值也已fail closed。

本 candidate 明确不提供正式结果的独立可重放证据。以下条件已登记为新的
execution-successor硬门：

1. 对注册 input manifests、`541/530/34/34`数量和跨split不相交做递归闭合；
2. 保存native solver evidence及primal solution，并独立重算约束残差；
3. 以content-addressed chunks持久化holdout trajectory并从轨迹重算metrics；
4. 保存bootstrap draw-stream hash和replicate endpoints，或独立完整重算CI；
5. 从sealed scientific/implementation outer和input manifests内部派生provenance
   authority；
6. streaming persistence、resumable checkpoints、bounded-memory profile、
   runtime projection及单独R3 execution-successor review。

因此当前`formal_execution_ready=false`、`formal_result=false`、
`paper_claim=false`和`security_certified=false`。上述缺口是正式执行证据阻塞，
不是数学不可行或V5科学设计失败。

v1 inner/outer SHA-256分别为
`e2039c4505ca72c53aae1c75844a431165cdaf993ab275d14bbdbde5bed4a4f7`和
`61493905239137a3e82093ce3da0daa75b86f82f3ff47a30e7bcc29097298699`。
全新 independent R3 reviewer 的 official verdict 为 `REWORK`：
`Blocker/Major/Minor=0/4/1`。machine-readable receipt 为
`configs/rq2_joint_deliverability_implementation_review_rework_v1.yaml`，
SHA-256 为
`5ee80168459bef736f25d833697bbb80498a72923edd4f995ce5680b24f907c0`。
四项 Major 分别是 full-support fallback certificate 未与 audit 闭环、
network-only 相同 planning hash 未强制完整证书同一、outer 未封存本地 solver
依赖，以及 success rename 后 parent fsync 失败可被 readback 重分类为成功。

v1 的 8 个 sealed members 保持不可变。唯一一次聚焦 v2 successor 使用独立
versioned model/scenario/evaluation/runner/
validator/test/architecture 路径，内聚 residual 审计并显式登记
`src/rq2_joint_deliverability_v2/solver_adapter.py`，同时增加四类 reviewer 反例
和 fresh-process import closure oracle。两轮 pre-seal audit findings 已闭合为
`0/0/0`；focused `71/71`、related `215/215`、Ruff/format、validator 和 module
入口均通过。v2 inner/outer SHA-256分别为
`2344e72026a9ff8e113bfbb7e4ca232329c525c6910df52a288dbd23ca39f20b`和
`e086f13cca12e198fd69553bc574662d615ab09b343ac6619e2448b94a7f2ee2`，
状态为`SEALED_READY_FOR_INDEPENDENT_REVIEW`。全新 reviewer 的唯一 official
R3复审为`PASS`，`Blocker/Major/Minor=0/0/0`。machine-readable receipt 为
`configs/rq2_joint_deliverability_implementation_review_pass_v2.yaml`，
SHA-256为
`67beedbaa1c54118c0039acc1d8b038b7e0aada5ba416b6a9b5949d46ead30d3`。
该PASS只关闭reference implementation review gate；execution successor仍受本节
登记的输入、primal、trajectory、bootstrap、provenance、streaming、checkpoint、
memory与runtime硬门约束。所有formal/result/claim/security门继续关闭。

#### 联合服务可交付前沿 execution successor v1 REWORK 与 v2 ESCALATE（2026-09-05）

用户授权的平台无关 execution evidence/resume infrastructure 已完成构建、封存和
独立 R3 审查；该授权不包括正式 46-cell、1,071-block grid、holdout、transport、
bootstrap、结果发布或论文/安全 claim。

execution v1 实现了注册输入递归审计、grid checkpoint 全量重放、strict JSON/CSV、
native primal capture/replay、planning evidence index、content-addressed holdout、
两遍式 resume、bootstrap certificate replay、原子持久化和 bounded working set。
v1 inner/outer SHA-256 分别为
`e9274340b35282923ff7fc50b308a56fe1079868d22c02162b73d5bf14658a86`和
`1ec234a1279b1c5a09b2beedb66ec1dfffcda28ed4a024df44d7d47060c976d2`。
official R3 review 发现一项 Major：sealed live config 被测试以
`require_sealed=false`校验，使登记的 focused command raw-red，并使
opened-gate 反例在 lifecycle 层提前失败。REWORK receipt 为
`configs/rq2_joint_deliverability_execution_review_rework_v1.yaml`，SHA-256 为
`9188549f0fc87b7094ff6f1422a36e36ee45718338aa4bc9230edcfee47ede5a`。

v1 的 19 个 sealed members 保持不可变。唯一聚焦 v2 successor 只修复
lifecycle-aware live validation、显式 draft fixture、opened-gate 精确错误断言和
versioned predecessor authority；科学协议、solver、evidence schema、持久化与
resume 逻辑不变。v2 pre-seal findings 为`0/0/0`；post-seal focused 为
`139 passed, 1 skipped`，implementation-v2 + execution-v2 broad 为
`210 passed, 1 skipped`。唯一 skip 是 Windows native directory flush 执行机
probe，未计为通过。Ruff、format、py_compile、sealed validator、runner
`--validate-only`及21/21成员哈希复核通过，且保持0 solver、0 formal write。

v2 inner/outer SHA-256 分别为
`e757b8662ce12c4b93d5bc826e00c77ad905a945384a120157d8da18203a98c8`和
`ff70b138f61833908c84763c3a6df06ad255f6f6f26adfbf1e4051865a0e5f93`。
全新 reviewer 对 receipt 尚不存在时的 exact outer 初始给出`PASS`，
`Blocker/Major/Minor=0/0/0`。历史 PASS receipt 为
`configs/rq2_joint_deliverability_execution_review_pass_v2.superseded.yaml`，
SHA-256 为
`20c13ff59f47a76eb9aad6962884b8605aa7de76833cdf00abc62229bc7f1a35`。

该 receipt 物化后，v2 原样 focused command 变为
`138 passed, 1 failed, 1 skipped`：`_load_live_registered_inputs()`正确通过
review authority并在下一门报告 dispatched-grid manifest 未绑定，但 sealed test
仍固定匹配 review receipt 缺失。精确 deselect 后 focused/broad 分别为
`138 passed, 1 skipped, 1 deselected`和
`209 passed, 1 skipped, 1 deselected`，但 deselect 不满足 v1 REWORK 已冻结的
raw-green要求。独立 post-review adjudication 因同一验收项再次失败，将现行 verdict
修订为`ESCALATE`，`Blocker/Major/Minor=0/1/0`。ESCALATE receipt 为
`configs/rq2_joint_deliverability_execution_review_escalate_v2.yaml`，SHA-256 为
`969cd58f090cc9fa6dfba986715ec67a8e18dfcf8e188d97c11748f421895b6d`。
原 PASS receipt 仅在`.superseded.yaml`路径保留逐字节历史记录；sealed config
要求的固定 PASS authority 路径保持 absent，因此当前 core 必须 fail closed。

当前仍缺：
完整 dispatched-grid package、Windows x86-64 runtime receipt、Gurobi 13.0.2
native replay、注册规模 peak-memory、transport runtime projection、
fresh-process activation successor及单独用户 formal-run authorization。
因此`formal_execution_ready=false`、`formal_result=false`、
`paper_claim=false`和`security_certified=false`；不得启动 solver 或把缺失输入
解释为数学不可行。按`agent.md` §7，同一validation-contract验收项在唯一
REWORK successor中再次失败，禁止自动创建后续 successor；必须升级给用户或
`sol_modeler`重新授权。

#### 联合服务可交付前沿 execution successor v3 independent R3 PASS（2026-09-05）

用户已在 v2 `ESCALATE` 后明确授权新的 versioned execution successor 修复和
重新审查；该授权不包括 formal run。v3 保持 v1/v2 sealed bytes、科学协议、
solver、evidence schema、persistence/resume 和公开 stage 关闭语义不变，只修复
review-authority 状态测试：

1. public-stage closure test 不再读取 live fixed-path receipt；
2. 同一临时根依次验证 receipt absent、合法 present 和 tamper；
3. 合法 review 后独立验证准确停在 unbound dispatched-grid gate，且 input audit
   调用数为 0；
4. validator 递归重算 v2 outer/21 members 及 v1 outer/19 members，并绑定
   v2 `ESCALATE`、superseded PASS 和旧 fixed PASS clean absence；
5. 普通 entry 与 dangling symlink 分别作为单点 fault case，均不得冒充 absent。

首轮 pre-seal audit 发现 dangling symlink 漏检一项 Major；修复后全新复审为
`Blocker/Major/Minor=0/0/0`。sealed v3 inner/outer SHA-256 分别为
`0e3a71b660f2e8d8371561614abf0577d6b6a9e36e1a7521ad7ced5f88c989e2`和
`b153f0320fe9dfe961575be4836f4bcf4044836be4fa66618119fc08d4cbce80`，
22/22 members 重算一致。

receipt 物化前后，原样 focused 均为`144 passed, 1 skipped`，原样
implementation-v2 + execution-v3 broad 均为`215 passed, 1 skipped`；唯一 skip
是 Windows native directory flush 执行机 probe，未计为通过。official R3 verdict
为`PASS`，`Blocker/Major/Minor=0/0/0`。固定 receipt 为
`configs/rq2_joint_deliverability_execution_review_pass_v3.yaml`，SHA-256 为
`1d8312e1458ce73dc76863a4b5c85f95506272ec53eaa088e523127b6ce0fa41`。
post-review stability 复核为`0/0/0`；私有 loader 已验证 review authority，随后
准确 fail closed 于`dispatched grid manifest is not bound by the sealed
execution candidate`。

该 PASS 只关闭 independent review gate。当前仍缺完整 dispatched-grid package、
Windows x86-64 runtime receipt、Gurobi 13.0.2 native replay、注册规模
peak-memory、transport runtime projection、fresh-process activation successor
及单独用户 formal-run authorization。因此`formal_execution_ready=false`、
`formal_result=false`、`paper_claim=false`和`security_certified=false`；不得
启动 solver 或把缺失输入解释为数学不可行。

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

## 2026-09-02 frozen candidate流程治理决策

本次用户权限为documentation-only；未来candidate的权威治理规则仅见`agent.md` §7。核心commitment原则是：authoritative
outer与`SEALED_READY_FOR_INDEPENDENT_REVIEW`状态成功原子发布前，candidate仍是可迭代non-authoritative draft；发布后
bound bytes不可变且同version不得重封。该规则只对未来candidate生效。

当前V4仍为historical `ESCALATE`，V1–V4 sealed chain不追溯改写；当前无candidate、无V5、无formal-run authority。V5
任何阶段及formal run均未获授权，下一步必须等待用户明确授权创建V5 draft。

## 2026-09-06 RQ2 fresh-process activation v2 ESCALATE

execution successor v3 已取得独立 R3 `PASS`，但该 PASS 只关闭 execution implementation review gate。用户随后明确授权
构建、测试、封存和独立审查 fresh-process activation successor，未授权 46-cell、1,071-block grid、holdout、
transport、bootstrap、solver 或 formal run。

activation v1 inner/outer SHA-256 分别为
`c6c057d97b8accb268705f501d513fd3d3d2fa9b1238e9ea37d64a161d774585`和
`7672d1a6f3382e268b5ffa0b22a561e72615bb0b5dc419f0b48916652da860d4`，22/22 members 稳定。其 official
R3 verdict 为 `REWORK (0/1/0)`：逐段 `lstat` 后按完整 pathname 重开文件，无法阻止 ancestor directory 在两步之间
被替换。REWORK receipt
`configs/rq2_joint_deliverability_activation_review_rework_v1.json` SHA-256 为
`11363e30bfe497dfb1f6f8f35fbb3c44297300bdcc9fc68b2eae0a3afcd6093a`。

唯一 versioned REWORK successor v2 改为 descriptor/HANDLE-anchored component traversal。POSIX 使用 held parent
`dir_fd`、`O_NOFOLLOW`和`O_DIRECTORY`；Windows 从 volume root 开始，以 `NtCreateFile`、
`OBJECT_ATTRIBUTES.RootDirectory`和`FILE_OPEN_REPARSE_POINT`逐段相对打开。authority presence 使用两次完整
anchored snapshot；fresh child 使用`-I -B -S -X pycache_prefix=<fresh-empty-private-directory>`，并从 parent
digest-bound envelope 中执行已验证 source bytes。v1 ancestor-swap finding 已关闭。

v2 pre-seal findings 曾闭合为`0/0/0`。封存后 inner/outer SHA-256 分别为
`de024959d1557c87b43ee3eb56eb8cae10dfc879820dab7f315f2a7f08a82184`和
`34e35c91a5af25903582c21b6736254f2fe0cd2dea879b9a0c6858f67135b37d`，24/24 members 稳定。
post-seal sealed validator、fresh validate-only 均通过；focused 为`55 passed, 1 skipped`，current-state broad 为
`769 passed, 5 skipped, 1 deselected`。唯一 deselect 是已登记的 sealed execution-v1 历史状态断言。全部验证保持
0 solver call、0 formal result write。

全新 official reviewer 对 exact v2 outer 给出`ESCALATE (0/1/0)`。Major
`activation-v2-close-error-resource-ownership`指出：`_stable()`把 leaf fd 转交`os.fdopen()`后清空显式 owner，
context-manager close 失败时没有 ownership probe 或 bounded recovery；Windows exception cleanup 也丢弃 descriptor/
HANDLE recovery 结果。独立单点复现得到
`ActivationRejected: artifact descriptor read failed`且`leaf_fd_still_open_after_rejection=true`。现有测试只覆盖一次
POSIX ancestor close failure；Windows relative-handle 检查仍是源码字符串断言，未形成行为级 HANDLE close-failure
证据。

machine receipt
`configs/rq2_joint_deliverability_activation_review_escalate_v2.json` SHA-256 为
`5d94ca406f8e70309e000f85d1534e607241f87e1114bbf2d26e399c8d39c0da`。v2 是 v1 official REWORK 后的唯一
successor，按`agent.md` §7 不得自动进入另一轮修复；v1/v2 sealed bytes保持不可变，fixed PASS receipt路径保持
absent。当前 activation review gate未关闭，dispatched-grid package、Windows runtime receipt、Gurobi 13.0.2
native replay、registered peak-memory、transport projection、execution activation与user formal-run authority仍缺失；
formal execution/result/paper claim/security certification全部为false。后续versioned successor须由用户或
`sol_modeler`重新明确授权。

## 2026-09-07 RQ2 fresh-process activation v3 draft

用户已在 activation v2 `ESCALATE` 后明确授权创建 activation v3 并继续修复
`activation-v2-close-error-resource-ownership`。当前 v3 为
`DRAFT_NONAUTHORITATIVE`，production inner/outer manifest 与 PASS receipt 均
absent；本次授权不包含 seal、official review 或 formal run。

draft 已将 stable read 改为显式 leaf descriptor ownership，使用
`os.read/os.lseek`并在正常、read-error、first-pass close-error 与 replay
close-error 路径统一检查 bounded recovery 结果。Windows close recovery 与
relative parent-handle chain 已提取为可行为测试的 helper，ancestor HANDLE
cleanup failure 会同时回收 transferred leaf descriptor 后 fail closed。

当前 focused 为`60 passed, 1 skipped`；新增 5 个单点 fault tests 覆盖 leaf
close、replay close、read failure、Windows `CloseHandle` retry 及 Windows
relative-handle cleanup。该结果仅证明当前 draft 的针对性回归，不是
pre-seal audit、seal 或 independent R3 PASS。v1/v2 sealed bytes及 v2
ESCALATE receipt保持不变，所有 formal execution/result/claim/security gate
继续关闭。

全新只读 reviewer 对 commit `2e902c4` 的 live draft 完成非权威 pre-seal
audit，结论为`pre-seal findings = 2/2/1`：

1. Blocker：sealed-path 对 v3 outer/inner schema 仍传入
   `expected_version=2`，机械 seal 后验证必然失败；
2. Blocker：POSIX recovery 仅用`samestat`、Windows recovery 仅用 live
   boolean 判断 ownership generation。首次 close 已释放原对象但报告失败、
   同一 fd/HANDLE 数值被复用时，retry 会误关 replacement；
3. Major：Windows cleanup outcome未区分`closed/unresolved/indeterminate`，
   且以最后一个failure为cause，可能掩盖更严重的未关闭状态；
4. Major：fault matrix缺少已关闭、复用、retry failure、indeterminate probe、
   callback exception，以及Windows primary failure与cleanup failure组合；
5. Minor：activation controller模块说明仍标为v2。

主代理独立复现两个Blocker：v3 config version为3而sealed verifier要求2；
POSIX注入观察到同一数字fd被close两次且replacement最终`EBADF`，模拟Windows
观察到第二次close作用于replacement。审查前后六个输入hash一致、工作区干净、
0 file write、0 solver/formal effect。当前不得进入seal；须在同一
`DRAFT_NONAUTHORITATIVE`中修复并由新的只读pre-seal reviewer复审至`0/0/0`。

### 2026-09-07 activation v3 remediation（等待全新 pre-seal reviewer）

同一 `DRAFT_NONAUTHORITATIVE` 已实现针对上述 `2/2/1` findings 的修复候选：sealed-path
outer/inner version 改为 v3；close recovery 仅在显式 `same_generation` proof 后至多 retry
一次，production POSIX/Windows probe 只可证明 `closed`，数值存活、`samestat` 或 HANDLE
liveness 均不作为 generation proof；cleanup 以 `closed/unresolved/indeterminate` 结构化保留
全部 errors、primary failure 与最严重 outcome；controller 模块说明改为 v3。行为级 fault matrix
覆盖 already-closed、numeric reuse、retry failure、indeterminate probe、callback exception，以及
Windows primary failure 与多个 cleanup severity 的组合，并断言 replacement 保持存活及 exact
outcome。此段只记录 remediation implementation，尚无新的 reviewer verdict，不能把旧 findings
记为已独立清零。

activation-v3 focused 为 `61 passed, 11 skipped in 18.57s`；11 个 skip 精确为 3 个 POSIX-only
fault injection、1 个 POSIX descriptor-relative open，以及当前 Windows 无 symlink privilege 导致的
7 个 symlink tests。activation-v3 + implementation-v2 + execution-v3 原样 raw broad 为
`7 failed, 268 passed, 13 skipped in 456.64s`。7 个失败全部来自未修改的 sealed
`tests/test_rq2_joint_deliverability_implementation_v2.py`：

- `test_atomic_output_publication_has_exact_recursive_manifest`；
- `test_recursive_manifest_rejects_extra_empty_directory`；
- `test_publication_marks_post_result_failure_indeterminate`；
- `test_publication_cleans_up_failure_before_result_rename`；
- `test_publication_reconciles_transient_post_success_readback_failure`；
- `test_publication_keeps_success_parent_fsync_failure_indeterminate`；
- `test_output_publication_rejects_symlink_ancestor`。

前 6 个在 Windows directory `os.open` 的 `_fsync_directory` 处得到 `PermissionError`，最后一个因
WinError 1314 无 symlink privilege。该测试文件、implementation-v2 runner/validator 与
`src/rq2_joint_deliverability_v2` 均不 import 或引用 activation-v3，且本轮 changed paths 不含上述
sealed implementation 路径。同一 7-node 命令已在 clean HEAD
`e93eb573b4185c937a2a23ade6f0ceed614f6005` 独立 clone 原样复现为
`7 failed in 70.56s`，节点及 traceback 原因一致。精确 deselect 仅作为其余覆盖证据：
`268 passed, 13 skipped, 7 deselected in 406.59s`；不得把该结果描述为 raw broad green。

Ruff check/format-check 与 4-file `py_compile` 通过。static validator 与 fresh validate-only 均通过；
fresh inventory 为 closure `13/13`、observed/executed `11/11`，并报告
`solver_calls=0`、`formal_result_files_written=0`、`formal_execution_ready=false`。`--execute`
仍在 review-only boundary exit 1。production inner/outer manifest、activation PASS receipt、外部
authority 与 formal roots 均不得物化。下一步只能由另一名全新只读 reviewer 对当前 live draft
执行 pre-seal re-audit；在其 verdict 前保持 draft，不得 seal、official review 或 formal run。

### 2026-09-07 activation v3 第二轮 pre-seal findings：`0/3/0`

全新只读 reviewer 对第一轮 remediation 后的 live draft 给出非权威
`Blocker/Major/Minor=0/3/0`。该结论不打开任何 gate：

1. `_generation_safe_close.probe()` 在非法 status 时先返回，可能丢失同次 probe 返回的原始
   error；`same_generation` 或 `closed` 与非空 error 同时出现时也未统一强制
   `indeterminate`，前者仍可错误授权 retry；
2. POSIX `_path_presence_once` 的 traversal primary failure 未跨 finally cleanup 保留，cleanup
   finding 会以 `primary_error=None` 覆盖原始异常；
3. Windows 测试主要约束通用 generation helper，未直接冻结 production Win32 query 到
   `closed/indeterminate` 的映射，也未证明 `_windows_open_anchored()` 实际使用同一受测 adapter。

旧 `0/3/0` 作为第二轮审查事实保留，不得因后续 writer remediation 被改写为 reviewer 已清零。

### 2026-09-07 activation v3 第二轮 remediation（等待全新 re-audit）

同一 `DRAFT_NONAUTHORITATIVE` 已实现第二轮修复候选。probe 先保留原始 error，再验证 status；
任何非空 error、非法或畸形 status 均强制 `indeterminate` 且禁止 retry，只有 error-free exact
`same_generation` 可授权一次 retry。retry 后 generation 改变会保留两次 close error、标记
`indeterminate`并停止，replacement 不再被后续 close。POSIX presence traversal 已抽成直接可注入
的内部路径，先捕获 primary、完成全部 cleanup；cleanup 有 finding 时 `_CleanupFailure` 保留同一
primary 对象与全部 outcome，否则重抛同一 primary。模块级 production Windows adapter 冻结
successful live query→`indeterminate`、`ERROR_INVALID_HANDLE`→`closed`、其他 Win32 error→
`indeterminate`且保留 error；native wiring test 通过 monkeypatch 该模块级 adapter，证明
`_windows_open_anchored()` 实际调用同一对象。

新增单点矩阵为 `11 passed, 71 deselected in 1.63s`；完整 activation-v3 focused 为
`71 passed, 11 skipped in 15.86s`；受影响 activation-v3 + execution-v3 覆盖为
`214 passed, 13 skipped in 97.02s`。此前三文件 raw broad 的 7 个 sealed implementation-v2
Windows baseline failures 已在 clean HEAD 原样复现，本轮未修改该 sealed 路径，故仅复用既有
baseline 账目，未将其描述为 green。Ruff/format-check、4-file `py_compile`、static validator 与
fresh validate-only 通过；fresh closure/observed/executed 为 `13/11/11`，solver call/formal write
为 `0/0`。negative `--execute` 仍在 review-only boundary exit 1。当前不得宣称第二轮 findings
为 `0/0/0`；下一步仅为另一名全新只读 reviewer 的 pre-seal re-audit，期间不得 seal、生成
manifest/receipt 或启动 solver/formal run。

### 2026-09-07 activation v3 pre-seal `0/0/0` 与 production seal

第二名全新只读 reviewer 对第二轮 remediation 后的 live draft 完成非权威 pre-seal re-audit，
登记 `Blocker/Major/Minor=0/0/0`；历史 `2/2/1` 与 `0/3/0` findings 据此关闭，允许进入 seal，
但该结论不是 exact sealed outer 的 official verdict。commitment 前 focused 为
`71 passed, 11 skipped in 15.82s`，受影响 activation-v3 + execution-v3 为
`214 passed, 13 skipped in 98.32s`；Ruff/format-check、4-file `py_compile`、static validator、
fresh validate-only 与 negative execute 均满足冻结合同。此前 clean HEAD 已复现的 7 个 sealed
implementation-v2 Windows baseline failures 继续保留为 raw broad 红项，不描述为全绿。

production seal 先在系统临时目录以 Python production verifier 与独立 PowerShell
`ConvertFrom-Json`/`Get-FileHash` 两种机械方式复算，均得到 bundle `24/24`、Python closure
`13/13`、activation v2 predecessor `24/24`、execution v3 `22/22`。activation v3 inner/outer
SHA-256 分别为 `5f4bc77aabff64cc6b4b8c257bd955a6315548a6a24eebdf607b815fbd21a262` 与
`f1fcd7e77b188778466319c993538db1100730026a89b884711fc51497409ee7`；outer 最后单独发布，
状态为 `SEALED_READY_FOR_INDEPENDENT_REVIEW`，24 个 bound members 自 commitment 起不可修改。

post-seal sealed validator 与 fresh validate-only 均通过，24/24 member replay、13/13 closure、
v2 24/24 与 execution-v3 22/22 复核通过；fresh observed/executed 为 `11/11`，solver call 与
formal result write 为 `0/0`。activation review receipt、dispatched-grid、runtime、execution
activation、user formal-run authority 及两个 formal roots 共 `7/7` absent，相关进程为 0。
当前没有 official activation PASS receipt；independent review、formal execution/result、paper
claim 与 security gate 均保持 false。下一步只能由另一名全新 official reviewer 审查 exact outer。

### 2026-09-07 activation v3 official R3 PASS

全新 official `sol_reviewer` 已对 exact activation v3 outer
`f1fcd7e77b188778466319c993538db1100730026a89b884711fc51497409ee7` 完成独立审查，最终
verdict 为 `PASS`，`Blocker/Major/Minor=0/0/0`。审查绑定 inner
`5f4bc77aabff64cc6b4b8c257bd955a6315548a6a24eebdf607b815fbd21a262` 与 24/24 members，
并复核 focused `71 passed, 11 skipped`、activation+execution `214 passed, 13 skipped`、
Windows 高风险矩阵 `6 passed`、sealed/fresh/Ruff/format/diff 与 0 solver/0 formal write。

machine receipt `configs/rq2_joint_deliverability_activation_review_pass_v3.json` 的 SHA-256 为
`3bc4751d2478e9e216e829233ec21dc96c5340f4d81ebae4dcd46ec222f3ddd8`；其 reviewer role/model
分别为 `independent_sol_reviewer`/`gpt-5.6-sol`，`reviewed_on=2026-09-07`，三类 finding arrays
均为空。official report 不含 cryptographic signature，receipt exact schema 不添加额外 provenance
或 evidence 字段。

该 PASS 只关闭 activation review gate。receipt-aware sealed validator 与 fresh validate-only 通过，
fresh blocker 仅剩 dispatched grid、runtime、execution activation 与 user formal-run authority 四项；
negative execute 仍在 review-only boundary exit 1。其余四项 authority 与两个 formal roots 共
`6/6` absent，formal execution/result、paper claim 与 security 均为 false，相关进程为 0。
历史 raw broad 的 7 个 sealed implementation-v2 Windows publication baseline failures 继续作为
残余风险保留，不描述为 broad green。

## 2026-09-08 public-grid HiGHS formal activation V5 writer remediation（等待独立 pre-seal audit）

V4 official R4 `ESCALATE` receipt
`configs/rq2_public_grid_highs_formal_activation_successor_review_escalate_v4.json`
（SHA-256 `1d4f5f1b65512a0092438051055171c5abf4dbbe2aa358675c5f580636bc4e9c`）登记的
`V4-POST-RELEASE-BASEEXCEPTION-GAP`、`V4-DUAL-TERMINAL-RACE` 与
`V4-TEST-MATRIX-GAP` 已在同一个 V5 `DRAFT_NONAUTHORITATIVE` 中形成 writer remediation。
V5 使用单一跨进程 lifecycle decision 和全局 terminal decision；success/unresolved 竞争者共享同一
create-if-absent authority，loser 必须校验磁盘 winner。release persist、stable readback、phase return、
acceptance persist 及 recovery 的 `KeyboardInterrupt`/`SystemExit` 窗口均进入 fault matrix。

本轮独立代码核查另发现一个未被原矩阵覆盖的 post-commit 窗口：terminal JSON 已完成原子 hard-link
commit，但 stable readback 之前发生 `KeyboardInterrupt` 或 `SystemExit` 时，原实现会让异常逃逸，磁盘上的
terminal class 与 controller return code 可能矛盾。先加入 success/unresolved ×
`KeyboardInterrupt`/`SystemExit` 四例复现；初始 `KeyboardInterrupt` 注入在 32.86s 后中止 pytest，未完成
测试。最小修复只在 terminal path 已是 ordinary file 时重新读取并严格验证磁盘 authority，否则继续抛出；
修复后四例为 `4 passed in 340.46s`。15-node 受影响矩阵为
`15 passed, 38 deselected in 1290.35s`，覆盖 release 三类窗口、双进程 terminal 三种竞争、terminal
post-commit reconstruction、正常 success 与 block-zero exception。

final exact-byte V5 focused 为 `53 passed in 4028.14s`，0 failure、0 skip。正确 related 范围为
activation V1–V4 + V8；精确排除三个已登记的 V8 历史状态节点后为
`106 passed, 3 deselected in 76.42s`。raw V8 必须保留为
`63 passed, 3 failed in 13.53s`，三个 failure 精确是
`test_execution_review_gate_precedes_v8_production_lease_touch`、
`test_bundle_live_closure_new_roots_and_review_absence`、
`test_canonical_validate_only_and_execute_remain_review_gated`；它们是 V8 已运行后失效的
review/lease/root-absence 断言，不得把 raw broad 写成 green。

Ruff check/format-check、4-file in-memory compile 与独立 `modulefinder` exact-set oracle 均通过；无 `.pyc`
写入。bootstrap/controller validate-only 均 exit 0，保持 1071 blocks、HiGHS 1.15.1、4 threads，
并报告 solver/formal-root write=`0/0`。当前 80-member closure digest 为
`a0a9d1429e516bbdd0c42ca30155a6174de3b736495bd1c0f905d3e475a248c2`，但 authority 仍仅为
`derived_current`，`expected_hashes_verified=false`，不是 frozen execution closure。negative
`--execute` 在 draft gate exit 1，未进入 preflight、consume 或 spawn。测试后相关进程为 0，五个计划
checkpoint/worker/log/output/activation roots 全部 absent，production inner/outer/closure、review receipt、
run authority 与 lease 均未物化；V4 outer、77-member closure及两份用户 PDF 的受保护 hash 保持不变。

用户已授权继续 V5 的后续门禁流程，并允许在全部 gate 闭合后进入正式 1071-block run；本 checkpoint
只完成 writer 级 DRAFT/PRE_SEAL 证据，未把该授权物化为 run-authority artifact。当前
`writer_pre_seal_evidence_complete=true`，但 `pre_seal_findings_closed=false`、
`sealed_ready_for_independent_review=false`、formal/result/claim/security 均为 false。下一步只能由全新
只读 R4 reviewer 对 live exact bytes 做非权威 pre-seal audit；在 reviewer verdict 前不得 seal、生成
production/review/authority artifacts 或启动 solver/formal run。

### 2026-09-08 V5 fresh pre-seal 2/0/0 findings remediation（等待再次独立复审）

全新只读 pre-seal reviewer 对上一 writer checkpoint 登记了非权威
`Blocker/Major/Minor=2/0/0`；该历史 verdict 不打开任何 gate。B1 是 controller 已严格提交并返回
terminal `success` 后，在 guard 返回前发生 `KeyboardInterrupt`/`SystemExit` 时，outer exception path
虽接受磁盘 success winner 却继续重抛，造成 success terminal 与 child nonzero return code 矛盾。B2 是
release acceptance 已验证到 controller protected envelope/immutable spawn receipt 之间仍有 exit race，
bootstrap 可能把已退出 child 写成 receipt，随后 strict readback 失败而未形成 lifecycle/terminal closure。

两项均先保留 test-first red。B1 的 `KeyboardInterrupt` 注入曾直接逃逸并在 88.44s 后中止 pytest，未完成
测试；B2 的 dead-child `rc=17` 复现为 `1 failed in 31.17s`，并错误进入 committed-spawn recovery。最小
实现保持 validator、PID/create-time、timeout 与 one-shot/gate order 不变：严格 global terminal winner
现在决定 controller exit 语义，只有 success winner 且已取得完整 result 才正常返回，unresolved winner
继续传播异常；acceptance 之后的 controller path 整体进入 `BaseException` envelope。bootstrap 在 immutable
spawn receipt commit 前先严格校验 prospective payload，并在 commit 两侧之前完成两次 exact PID/create-time
liveness 证明；receipt commit 确认后的第一操作仍是 postcommit fault hook，随后才做 strict disk readback；
precommit dead-child 分支归入 pre-spawn post-release recovery。没有放松 unresolved/timeout 语义，也没有将其
解释为 infeasible。

精确六个旧失败与四个 sibling 最终为 `10 passed in 1643.39s`。首次 full 暴露两项测试夹具预期差异，账目为
`59 passed, 2 failed in 6620.97s`：dual-contender fixture 缺少显式 arrivals 诊断，cross-attempt replay regex
遗漏更早且同样严格的 `dynamic pre-seal authority drifted`。仅修夹具后两点为 `2 passed in 71.04s`；
controller-owned race 独立重复三次均通过，并继续断言 300s bounded rendezvous、cancel/controller 两条真实
arrival、controller winner、无 thread error 与 postcommit-first fault window。最终 exact-byte V5 full 为
`61 passed in 6425.67s`，0 failure、0 skip；activation V1–V4 + V8 current-state related 为
`106 passed, 3 deselected in 80.01s`。raw V8 历史账目仍是 `63 passed, 3 failed in 13.53s`，三个已登记
review/lease/root-absence 节点不得称为 raw broad green。

Ruff/format、4-file in-memory compile、双 validate-only、negative execute 与独立 `modulefinder` exact-set
均通过。derived closure 为 80 members，digest
`5ef558bfd51eb17d0e217dd254a0c23e52e702a84c9692d98e86a24b75e3cc6c`，仍明确是
`hash_authority=derived_current`、`expected_hashes_verified=false`，不是 frozen commitment。最终相关进程
为 0；五个计划 roots 与七个 candidate production/review/authority/lease artifacts 均 absent。V4 outer
`6936d06a5bc8d191f5eaf235fe7784c36193ac6343d88d16cbbd3e5bea8d2068`、V4 closure
`ba9195283cf3ad149e08c875820198648d0a9c0cf6b99ac7e3c37b212683b948` 的 77/77 replay，以及两份用户
PDF hash 均保持不变。

本段只登记 writer remediation 与可复核证据，不把历史 `2/0/0` 自行改写成 `0/0/0`。PRE_SEAL audit
保持 `pre_seal_findings_closed=false`、`sealed_ready_for_independent_review=false`，且 formal/result/claim/
security 全为 false。当前状态是可供另一名全新只读 R4 reviewer 执行独立非权威 pre-seal re-audit；在其
verdict 前不得 seal、生成 production/review/run-authority/lease artifacts 或启动 preflight/solver/formal run。

### 2026-09-10 V5 fresh pre-seal 1/1/1 findings remediation（等待全新独立复审）

在上一 `2/0/0` remediation checkpoint 之后，另一名全新只读 pre-seal reviewer 对当时 live exact bytes 登记
`Blocker/Major/Minor=1/1/1`。Blocker 是 bootstrap 在 validated acceptance 后、spawn-receipt protected
recovery 前仍有一条可注入 `KeyboardInterrupt`/`SystemExit` 的 executable line gap；Major 是 ordinary
stable-byte helper 仍按 pathname 重开文件，不能证明 ancestor/endpoint 在读取期间保持同一对象；Minor 是
Windows 8.3 absolute alias prepare 后不能通过同一 canonical validator。该历史 verdict 不打开任何 gate，且不会
被 writer 后续结果改写为 reviewer `0/0/0`。

同一 V5 draft 的 remediation 将 acceptance 后完整 bootstrap 区间并入统一 `BaseException` envelope；ordinary
JSON 读取改为 descriptor/handle-anchored traversal、ancestor 与 endpoint identity 复核，并 fail closed 拒绝
symlink/hardlink/reparse、ancestor swap/read/swap-back 与不确定 cleanup；Windows 8.3 alias 和 canonical long path
使用一致 round-trip。line-gap 两个真实进程参数为 `2 passed in 248.46s`。首次 70-test full 是
`69 passed, 1 failed in 7393.36s`；唯一 failure 为旧夹具仍 monkeypatch `Path.is_symlink`，替换为真实
symlink 或 Windows junction/reparse parent 后精确节点 `1 passed in 217.36s`，production code 未改变。

随后完整运行发现一个独立的 startup performance blocker：`63 passed, 7 failed in 8435.02s (2:20:35)`；七项
均严格落为 unresolved，原因是 91-member closure 的 full dynamic-authority validation 经 nested
protocol/startup/runtime APIs 重复执行，spawn receipt 未能在冻结 30 秒 supervision timeout 内发布。最小修复不
改变 timeout，只完整验证 dynamic authority 一次并把同一 stable validated snapshot 传给已有 nested APIs；这些
API 仍对 authority 做 stable-byte reread/equality check。新增 exact-one-call regression 为
`1 passed in 24.64s`，原七项失败矩阵为 `7 passed in 13:59`。同步 pre-seal audit hash 前的 full 如实为
`70 passed, 1 failed in 4471.92s (1:14:31)`，唯一红项是 stale exact hash binding；同步后 binding 节点
`1 passed in 0.22s`，最终 exact-byte V5 full 为 `71 passed in 4520.02s (1:15:20)`。

activation V1–V4 + V8 current-state related 为 `106 passed, 3 deselected in 72.76s`，raw V8 的三项历史
review/lease/root-absence failure 账目不变。Ruff/format、4/4 in-memory compile 且 0 pyc、bootstrap/controller
validate-only、negative execute draft gate 与独立 `modulefinder` exact-set 均通过；solver/formal write=`0/0`。
当前 derived closure 为 91 members，digest
`ff11e25901b75387ce3b5b37278ed964ed93ab694ed760d27cf566a9d030c895`，仍为
`hash_authority=derived_current`、`expected_hashes_verified=false`。

最终 related process=0；五个计划 formal/activation roots 与七个 candidate production/review/run-authority/lease
paths 全部 absent。V4 outer SHA-256
`6936d06a5bc8d191f5eaf235fe7784c36193ac6343d88d16cbbd3e5bea8d2068`、V4 closure SHA-256
`ba9195283cf3ad149e08c875820198648d0a9c0cf6b99ac7e3c37b212683b948` 的 77/77 replay，以及两份用户 PDF
hash 均保持不变。当前只允许 `writer_pre_seal_evidence_complete=true`；
`pre_seal_findings_closed=false`、`sealed_ready_for_independent_review=false`、formal/result/claim/security 均为
false。下一步必须由另一名全新只读 R4 reviewer 对当前 live exact bytes 做非权威 pre-seal re-audit；其 verdict
前不得 seal、生成 production/review/authority/lease artifacts 或启动 preflight/solver/formal run。

### 2026-09-10 V5 fresh pre-seal 0/1/0 evidence remediation（等待下一名独立复审）

全新只读 pre-seal reviewer 对上一 writer checkpoint 给出 `REWORK`，分级为
`Blocker/Major/Minor=0/1/0`。Major 是 ancestor swap 测试仍 monkeypatch `Path.lstat/read_bytes`，而 live
`_ordinary_stable_bytes` 仅使用 `_open_ordinary_anchored`、descriptor `fstat/read` 与 production close；旧注入从未
执行且无调用计数断言，却在 audit matrix 中登记为 rejected。该证据诚信缺口使上一 checkpoint 不可 seal。

同一 draft 只修正测试证据：注入现发生在 live `_open_ordinary_anchored`/`_close_ordinary_descriptor` seams，
明确断言 swap/restoration 各一次、anchored open/close 各两次，并证明首个 descriptor identity 是 alternate file。
首个有效版本因在 descriptor 仍打开时 swap-back 而于 Windows 得到 `1 failed in 0.55s`、`WinError 5`；把恢复
放到 production close 完成后，第一轮 descriptor 读取 alternate，第二轮 replay 打开 restored original，strict
identity gate 以 `stable file identity drifted` fail closed。精确节点为 `1 passed in 0.36s`，相邻 anchored
replacement/link/cleanup/Windows path 矩阵为 `7 passed, 64 deselected in 19.30s`。production code 未改变。

同步 current test SHA-256 后，final exact-byte V5 full 为
`71 passed in 4573.00s (1:16:12)`；Ruff check/format 与 4/4 in-memory compile（0 pyc）再次通过。最终
related process=0，五个计划 roots 与七个 candidate production/review/run-authority/lease paths 均 absent，
solver/formal execution 未启动。PRE_SEAL audit 当前允许 `writer_pre_seal_evidence_complete=true`，但继续保持
`pre_seal_findings_closed=false`、`sealed_ready_for_independent_review=false` 与全部 formal/result/claim/security
flags=false。下一步须由另一名全新只读 R4 reviewer 复审当前 live exact bytes；本轮 0/1/0 reviewer 不得复用。

### 2026-09-10 V5 production-seal design audit：四项生产路径阻塞开放

修正 ancestor-swap fault injection 后，一名全新只读 reviewer 对当时实际覆盖的 pre-seal 路径登记
`Blocker/Major/Minor=0/0/0`。随后只读 R4 production-seal 设计核查发现四个此前未被真实生产分支覆盖的
阻塞，故该有限范围历史结论不能关闭当前 gate：

1. `V5-PRODUCTION-RUNTIME-AUTHORITY-GAP`：V5 runtime authority 缺少真实 worker runtime evidence
   必需的 HiGHS package init、Python source 和 binary 的 path/SHA-256；
2. `V5-PRODUCTION-DYNAMIC-CLOSURE-REVALIDATION-TIMEOUT-GAP`：production dynamic validator 经嵌套
   mapping/preflight 调用重复约五次完整 91-member closure，可能越过未改变的 30 秒 startup 门；
3. `V5-ONE-SHOT-CONSUMED-DESTINATION-RACE`：`consumed.exists()` 与 `os.replace(fresh, consumed)` 之间
   存在 destination overwrite 竞态，必须改为 destination-exclusive create-if-absent 消费协议；
4. `V5-SEALED-AUTHORITY-PLACEHOLDER-GAP`：sealed bundle/fresh lease/review/user authority 仍需 strict
   exact-key validation，`require_sealed_for_execution()` 仍为 draft 占位，且 `production_artifact_paths()`
   不能正确展开 one-shot mapping。

当前仍是同一 `DRAFT_NONAUTHORITATIVE`；未生成 production inner/outer/closure/lease/review/user authority，
未创建 formal roots，未启动 solver 或 1071-block formal run。机器字段恢复为
`writer_pre_seal_evidence_complete=false`、`focused_tests_passed=false`、
`pre_seal_findings_closed=false`、`sealed_ready_for_independent_review=false`，所有 execution/result/claim/
security flags 继续为 false。解除条件为四项修复与对应 fault injection、生产路径完整 closure call-count
`==1`、真实零-solver startup `<30s`、完整及相关回归全部通过，并由新的只读 reviewer 再次审查 exact bytes。

### 2026-09-10 V5 production-path remediation complete（等待 fresh pre-seal review）

四项开放 finding 已在同一非权威 draft 内完成 writer remediation：

- runtime authority 增补并复核 locked Python 与 HiGHS package init/Python source/binary 的 path/hash，真实
  `Highs` instance probe 保持 `solver_solve_called_by_runtime_probe=false`；
- production dynamic authority 对 frozen closure 只做一次完整验证，再传递 closure/static/preflight/review/user
  snapshots；实际 91-member frozen closure call count=`1` 且低于冻结 30 秒，real block-zero zero-solver
  production sandbox 为 5.92s；
- one-shot consume 使用 destination-exclusive hard-link reservation 后不可逆 unlink fresh，再原子替换 consumed
  为 tombstone；双 spawned contenders 精确一胜一拒，预存 destination 不覆盖，link-return 后 BaseException 与
  unlink 后 tombstone failure 均保持 fresh absent；
- sealed bundle gate、fresh lease、review/user receipts 与 nested one-shot paths 已实现 strict schema/exact-key/
  hash binding，sealed gate 不等于 independent review 或 formal-run authority。

第一轮 full `80/80 in 4762.79s` 后 Ruff 发现的唯一 unused `noqa`/format 项导致 exact-byte style-only 更新，故
该轮只保留为 intermediate evidence。最终 current exact-byte full 为
`80 passed in 4804.17s (1:20:04)`；related V1–V4 + V8 current-state 为
`106 passed, 3 deselected in 77.10s`。Ruff/format、4/4 in-memory compile、独立 modulefinder exact-set、
bootstrap/controller validate-only 与 negative execute draft gate 均通过；current derived closure 为
91 members/digest `997b96c1269a7d1780158cf11836d530774578c2b0f4f1b8753c5cebd6fd21ae`，仍为
`derived_current`、`expected_hashes_verified=false`。

最终相关进程、五个 planned roots、十个 production candidate artifacts 全为 0，solver/formal write=`0/0`。
机器状态现为 `writer_pre_seal_evidence_complete=true`、`focused_tests_passed=true`，但继续保持
`pre_seal_findings_closed=false`、`sealed_ready_for_independent_review=false` 及全部 execution/result/claim/
security flags=false。当前唯一下一步是新的只读 `sol_reviewer` 对这些 exact bytes 做非权威 pre-seal
re-audit；其明确闭合四项 finding 前不得 seal，其结论也不能授权 formal run。

### 2026-09-10 V5 production pre-seal second-BaseException/lifecycle blockers

fresh production reviewer 对上一组 exact bytes 登记非权威 `REWORK`，
`Blocker/Major/Minor=2/0/0`：

1. `V5-ONE-SHOT-SECONDARY-BASEEXCEPTION-GAP`：旧 hard-link reservation 在首次中断后进入 cleanup，
   cleanup 第一条 presence/stat/unlink 路径再次中断可留下 fresh+consumed 同 inode；test-first 实际复现
   为 `fresh_exists=true`。
2. `V5-POST-SEAL-VALIDATION-LIFECYCLE-GAP`：validator report、测试与 audit selector 中的 DRAFT-only
   断言会在 canonical seal 后失败或误报，因 sealed inner 会冻结这些 bytes，不能留待 seal 后修复。

writer remediation 将 one-shot 的不可逆点提前为 exclusive reservation directory：reservation 一旦创建，
fresh verifier 必须拒绝；随后仅由 reservation winner 执行 Windows 原子 move、stable validation 与 tombstone
replace，只有 exact tombstone 稳定后才移除 marker。双中断红例已转绿；预存 consumed 不被覆盖；move 后
中断与 tombstone failure 均保持 fresh absent；move 前中断虽可保留 fresh 文件，但 reservation marker 使其
不可复用。双进程 contender 连续 10 次均精确一胜一拒。

生命周期修复使用 draft/canonical 三组 selector，并让 bootstrap/controller validate-only schema/status 与
实际选中 config 一致；execute 的 sealed 分支在 review PASS absent 时仍于 preflight/consume/spawn 前拒绝；
closure 与 audit binding 测试按 selected lifecycle 验证。当前 targeted 为
`13 passed, 70 deselected in 13.68s`，production/review/one-shot 为
`28 passed, 55 deselected in 992.15s`，完整 V5 为
`83 passed in 4849.27s (1:20:49)`，related current-state 为
`106 passed, 3 deselected in 76.84s`。current 91-member derived closure digest 为
`8dec02efa845120bf7134cd04332012750a83e85eac309263b9c647b06a7bba8`，不是 frozen authority。

最终 process/roots/canonical-production-reservation census 为 0，双 validate-only 保持 1071 blocks、HiGHS
1.15.1、4 threads、solver/formal write=`0/0`，negative execute 仍在 draft gate exit 1。writer evidence 已完整，
但 reviewer findings 尚未由 fresh review 闭合：`pre_seal_findings_closed=false`、
`sealed_ready_for_independent_review=false`，所有 formal/result/claim/security flags=false。禁止在新的只读
R4 reviewer 给出明确 `0/0/0` 前 seal 或启动 formal run。

## 2026-09-10 V5 post-seal trace-scope timeout 与 V6 successor gate

V5 canonical bundle 已封存；outer/inner/execution-closure SHA-256 分别为
`7d6a217ab1536e52b37180d5a1fa5b715eb03980ae3cbb3e4de2e9fd315e64ea`、
`5cca0675bfd9a0b624287cf2705d089a4044493eacfa54c6ac82e074227c1a03`、
`f844b0ef12cf8111e533d13104d02e41e70eafbc6d1b56972dfd267fbdf5b08e`。post-seal full validation 为
`81 passed, 2 failed in 294.94s`；两个失败 child 均以
`startup control timed out: science_release.json` fail closed，正式 solver 未启动，不能解释为不可行。

blocker `V5-POST-SEAL-TRACE-SCOPE-TIMEOUT` 的根因位于封存测试的 fault-injection tracer：全局 tracer 在两次
91-member post-spawn closure replay 期间持续接收 nested call/line events。完整负载时第一段
handshake→ack 为 3.235 秒，child ack→ready 为 15.510 秒，第二次 parent replay 的 ready→release 为
34.744 秒，越过未改变的 30 秒门。不得以增大 timeout、跳过节点或复用 production closure snapshot 来关闭该
blocker，因为这会削弱冻结 stable reread/equality 与 TOCTOU gate。

V5 sealed bytes 保持不可变；最小 remediation 已进入 V6 draft/formal-controller V7 namespace，且唯一行为变化在
test-side injection seam：真实 release acceptance 返回后才给 `_spawn_controller` caller frame 安装 line tracer，
随后仍在登记的 exact line 注入一次。两个异常参数转绿后又连续三轮通过，并与正常 real two-process zero-solver
probe 合跑通过；最终 V6 为 `83 passed in 5143.15s`，related current-state 为
`106 passed, 3 deselected in 82.10s`。独立 modulefinder exact closure 为 91 members/digest
`86008a26f172cd5dcfe8881c8f9bcd883918d65b2f45d115772c19c2dfa24756`；Ruff/format、4/4 parse、双
validate-only 和 negative execute gate 均通过，solver calls/formal writes=`0/0`。

当前该 blocker 仅在 writer 证据层完成 remediation，尚未由 fresh independent R4 review 关闭。V6 canonical
manifest/seal/lease/review/user-authority 与五个 formal roots 全 absent，related process=0；V5 fresh lease
`4fc3da709214be3d8ea358b73a12e963ab18911db2fa414560a4c4636e45118c` 未消费，sealed hashes 未变。
机器状态保持 `writer_pre_seal_evidence_complete=true`、`pre_seal_findings_closed=false`、
`sealed_ready_for_independent_review=false`，所有 execution/result/claim/security flags=false。下一步只能由 fresh
只读 R4 reviewer 审查 live exact bytes；在其明确 `0/0/0` 前不得 seal，更不得把 writer test PASS 当作 formal-run
authority。

## 2026-09-10 V6 sealed-ready：post-seal validation complete

V6 PRE_SEAL reviewer `/root/v6_preseal_reviewer` 已对 live draft 登记非权威 `PASS 0/0/0`，关闭 pre-seal
findings 并仅允许 production seal。V6 已按无循环 publication DAG 封存，outer 为最后且 create-if-absent 的
commit point；其 SHA-256 为
`12a00b1c4a75943c81e712bc02f53ed38d67a6749e440c1103294a3c568937aa`。inner SHA-256 为
`6e4470ea6903c34aac046ca22f8aff043a1ae3a22a474d8ab886c84070718ee3`，包含 contract exact set 的
15 members；closure file SHA-256 为
`535bb0eba4c36b58efd45711f1e9fffbcaf65f703754517896fd67c7b0c3c0e4`，91-member digest 为
`e03b7d3e41708cc679acf14b16764531cfe7bdcbdf42875d1068a0643f9e62b1`。inner `15/15`、closure
`91/91` 的 stable replay、ordinary-single-link、hash/schema 验证全部通过；fresh lease SHA-256 为
`da599ee30522cd6597636bf8317ac8a90f518650a757cebc52ef41f57d325612`。

root 独立 post-seal 证据为：sealed targeted `11 passed in 385.25s`；V6 full
`83 passed in 5762.17s`；related current-state `106 passed, 3 deselected in 95.25s`；Ruff/format 与
4/4 parse green。双 validate-only 均 exit 0，继续报告 1071 blocks、HiGHS 1.15.1、4 threads、0 solver call、
0 formal-root write。negative execute 以 exit 1 在缺失 official review receipt 处 fail closed，fresh lease 未改变，
没有进入 preflight、consume、spawn 或 formal run。

最终 related process 与五个 formal roots 均为 0；official review receipt、V6 user authority、consumed lease、
reservation 全 absent，V5 sealed bytes/fresh lease 未漂移。状态现为
`pre_seal_findings_closed=true`、`sealed_ready_for_independent_review=true`；official review、formal execution、
result、claim、security 仍为 false。`V5-POST-SEAL-TRACE-SCOPE-TIMEOUT` 已在 V6 exact sealed bytes 中通过
post-seal validation，但 formal activation gate 仍由新的 official independent R4 review 阻塞；PRE_SEAL reviewer
实例不得复用为 official reviewer，且任何 review verdict 均不自动授权 formal run。

## 2026-09-10 V6 official ESCALATE 与 V7 draft successor

fresh official reviewer `/root/v6_official_reviewer`（independent `sol_reviewer`，`gpt-5.6-sol/high`）先对 exact
V6 outer `12a00b1c4a75943c81e712bc02f53ed38d67a6749e440c1103294a3c568937aa` 给出
`REWORK 0/1/0`：唯一 Major 是顶部权威状态总表仍停在 V4/V5 draft 语境。该文档 finding 已被最小修正，
但把修正后的非封存文档继续提交给同一 V6 outer 复核，没有按 `agent.md` 第7节在 official REWORK 后进入新的
versioned successor；同一验收项因此最终 official `ESCALATE 1/0/0`。machine-readable receipt 为
`configs/rq2_public_grid_highs_formal_activation_successor_review_escalate_v6.json`，SHA-256
`ee41fe26122862650fd492fe54aa950936f8cb38da21991b063130a771f6a2aa`；无cryptographic signature，
`execution_authority_effect=none`，且没有生成 V6 PASS receipt。

V7 已以 `DRAFT_NONAUTHORITATIVE` 建立，formal-controller 使用 V8 namespace。V7 明确绑定 V6 outer、
91-member frozen closure、canonical formal V7 config及上述 ESCALATE receipt；`frozen_science`、startup handshake、
runtime environment、模型/solver/threads/阈值、recovery、one-shot与per-block fresh-process语义均逐字继承 V6，
仅version/path/schema机械前移。test-first collection 在实现前以缺失V7 bootstrap `ImportError`转红；实现后绑定/
gate/保护哈希节点为`3 passed in 2.08s`，post-acceptance local tracer的精确
`KeyboardInterrupt`/`SystemExit`两参数为`2 passed in 264.92s`，并继续断言注入次数1、release acceptance、
唯一terminal、无`launch_incomplete`及owned child停止。

最终 V7 full 为`83 passed in 5348.26s (1:29:08)`，0 failure/error/skip；activation V1-V4 + V8
current-state related为`106 passed, 3 deselected in 77.93s`。Ruff/format、4/4 in-memory parse、独立
modulefinder exact-set及audit binding均通过。bootstrap/controller validate-only都exit 0，报告91-member
derived-current closure digest `7ba080085d223766954253ff76596fed98043252c58b3dc4115915326d2c2821`、1071 blocks、
HiGHS 1.15.1、4 threads、solver calls/formal-root writes=`0/0`；negative execute exit 1于draft gate。

最终 related process=0、五个V7 planned roots absent、11个V7 production canonical/lease/manifest/review/user/
reservation artifacts全部absent；V5/V6共11项受保护hash不变。当前仅
`writer_pre_seal_evidence_complete=true`；`pre_seal_findings_closed=false`、
`sealed_ready_for_independent_review=false`以及formal/result/claim/security全部false。下一步只能由fresh只读R4
reviewer审查当前V7 exact draft bytes；其明确闭合findings前不得seal，且本节不授权preflight、consume、spawn或
formal run。

## 2026-09-11 V7 PRE_SEAL REWORK remediation checkpoint

fresh只读R4 PRE_SEAL reviewer对V7给出`REWORK 1/0/0`。唯一Blocker为：V6 official ESCALATE receipt虽在
validate-only中校验，但未列入V7 future sealed inner member set，因此sealed execution gate不能在review、
user-authority、preflight、lease consume或spawn之前证明该receipt仍存在且内容未漂移。该verdict不产生执行权限。

整改采用test-first最小变更：先由新sealed execution-path regression证明expected inner set缺少该receipt，再仅把
`configs/rq2_public_grid_highs_formal_activation_successor_review_escalate_v6.json`加入inner member set；不复制
validator。测试通过真实`require_sealed_for_execution -> _verify_sealed_bundle`路径分别注入receipt缺失和内容漂移，
两种情况均在review/user/preflight/consume/spawn之前拒绝，五类调用计数全部为0。精确节点为
`1 passed in 0.57s`，七个lifecycle/closure/oracle focused节点为`7 passed in 20.06s`。

当前机器审计状态为`PRE_SEAL_REWORK_REMEDIATION_IN_PROGRESS_NONAUTHORITATIVE`；整改后的full V7 matrix尚未完成，
`writer_pre_seal_evidence_complete=false`、`pre_seal_findings_closed=false`、
`sealed_ready_for_independent_review=false`。V7仍为draft，formal execution/result/claim/security全部为false，且没有
正式运行。下一步仅为完成writer remediation matrix并提交fresh只读R4 PRE_SEAL复核。

## 2026-09-11 V7 生产授权链开发机验收与 preflight 写入顺序修复

### 1. 本轮范围

用户授权补齐V7真实生产路径验收；本轮保持同一未封存V7 draft，未创建successor、production seal、
review PASS或用户运行回执。所有合成授权只存在于带`NONAUTHORITATIVE_TEST_ONLY.json`标记的
pytest `TemporaryDirectory`；fresh子进程结束后自动清理。production源码保持原样复制，只有测试快照的
canonical配置选择及cwd重定位；18项快照用例使用16-member inner、91-member closure和77-member前序closure。

### 2. 实际缺陷与修复

`V7-PREFLIGHT-ALLOCATION-BEFORE-AUTHORITY-VALIDATION`：`_capture_preflight()`参数求值先调用
`next_attempt_root()`，然后才执行`preflight_authority_mapping()`。完整快照只注入lease reservation时，
校验虽然拒绝，却已创建activation目录；test-first为`13 passed, 1 failed in 66.02s`。
最小修复先取得verified mapping，再分配目录；4项focused为`4 passed, 12 deselected in 23.60s`。
阈值、lease消费协议、solver及科学配置未改变。该修复尚未完成fresh独立审查。

### 3. 已取得证据与边界

最终开发机Python 3.11.15 / pytest 9.0.2：`24 passed in 100.18s`，包括18项完整快照与6项相邻回归；
当前V7共收集101项，未运行全量。真实`bootstrap.execute`依次调用config/formal/closure/seal、
review/user、preflight及dynamic authority验证器，未替换这些gate。17个负例均单点注入且验证后续调用计数；
覆盖前序回执缺失/漂移、source/closure/outer/fresh漂移、review越权、user授权缺失或无效、
reserved lease、已有root、资源不足，以及dynamic发布后的回执或authority漂移。正常例独立复算modulefinder
exact-set，dynamic validator完整closure replay为1次且小于原30秒阈值。

OS进程枚举、available commit观测及非Windows进程创建时间是声明的测试替代边界；production spawn处硬停止，
科学loader被禁止。Windows分支要求真实locked runtime校验、原生no-replace consume和controller-side tombstone
回读；本机仅证明缺失Windows runtime及native consume会正确拒绝，不能记为Windows通过。
V5/V6 inner分别13/13、15/15，closure均91/91；activation v3静态sealed验证通过，冻结前序未改。

### 4. 未完成验收

本轮不证明真实sealed controller握手/终态、worker/resource journal、完整Windows回归或formal结果。
执行机须先运行新增快照矩阵，再完成当前101项及已登记related回归；验收矩阵必须逐项记录真实路径、
替代边界、fault计数、唯一终态、owned child停止和0 solver/formal-root write。fresh独立PRE_SEAL reviewer
完成前，`writer_pre_seal_evidence_complete=false`、`pre_seal_findings_closed=false`及全部运行门保持关闭。
执行命令见执行计划同日“V7生产路径验收交接”；历史83项green不得复用为本轮验收。

## 2026-09-12 RQ2 24小时终止边界诊断与 continuous successor 数据门

对sealed joint-deliverability v5的冻结training输入完成了非权威零solver必要条件审计。旧协议同时要求
CFE服务精确满足有效请求、对应track的`q`包含该服务，并在每个24小时block的hour 23强制inactive和
零债务。冻结541个power training blocks中，hour 23正CFE请求按
`alpha=0.50/0.70/0.85/1.00`分别为`358/478/541/541`个；因此后两档的每个raw training pair均触发
旧完成期CFE track的terminal-inactivity必要失败。该标签严格属于
`legacy_sealed_v5_single_24h_completed_period`，不适用于新的continuous observation边界。

审计保持sealed v5的46 cells和四臂inventory，并覆盖逐时available flexibility、energy、duration、
event-count乐观必要下界、总恢复下界、causal debt及旧完成期causal terminal debt。每cell有18,394个raw pairs；
available-flexibility违反数在`alpha=0.85, flex_fraction=0.20`时为18,394/18,394，说明只移除terminal
condition仍不足以产生非退化前沿。该投影可为含CFE track提供充分失败见证，但raw包没有dispatched
`grid_need`或E0；`network_only`、finite training support及完整物理可行性仍unknown，未触发必要条件不等于
feasible，也未运行任何solver。

用户已明确选择continuous multi-day service。新增
`configs/rq2_joint_deliverability_boundary_successor_v1.DRAFT.yaml`与
`docs/model_spec/rq2_joint_deliverability_boundary_successor_v1.md`只形成
`DRAFT_NONAUTHORITATIVE`合同：hour 23义务保留，跨chunk精确携带事件、duration/rest、event/energy预算、
recovery debt及prior-event状态；边界不恢复、不重置。split、arm/track、power trajectory/outage seed、
workload trace/normalization和provenance必须连续匹配。缺未来观察使completion right-censored；缺注册deadline
是completion合同缺失，均不抹去已观察到的服务或违规。

当前可执行组件只支持一个显式nonrolling accounting period并拒绝period切换；多period预算/reset、
deadline/recoverability来源、连续grid/CFE义务和holdout estimand必须在新的完整科学协议中先注册。
workload v3的`deadline_observed/checkpoint_observed/recoverability_observed`均为false，不能用任意零尾部或
虚构deadline补齐。additive `q=x_grid+x_cfe`只登记为分离义务的机制假设；co-benefit结算保持未决。

非权威机器包位于
`results/tables/rq2_joint_deliverability_boundary_diagnostic_v1_non_authoritative/`，其
`summary.json/cells.json` SHA-256分别为
`7702f71e27fedb608940f28565b03f27b78d11e0ae834f7247b3ed0a5c896080`/
`6f9bf70818d80872d3454da5e653c409273305b4165bef8f30f18941357a2db4`，绑定输入及audit/boundary/runner实现，
并明确`solver_calls=0`、formal/result/claim/security全false。focused为`50 passed in 29.55s`；最终静态及
文档回读另按本轮命令记录。下一步先完成continuation数据可用性审计和完整versioned continuous protocol，
再实现正式planner并交fresh独立R4 review；V7 Windows执行/授权问题是另一流程与计算blocker，不能替代
本节科学blocker的关闭。

## 2026-09-12 RQ2 frozen-margin continuation availability 证据

新增非权威零solver审计逐成员绑定power v4/workload v3 manifests、builder configs/实现及power N-1
chronology，并逐字节验证上一轮boundary config/code/result未漂移。power 1,071 blocks按split×seed形成
6条连续片段，training/holdout block links为538/527；workload 68 blocks按split形成2条片段，各33 links。
双侧同时有下一块的Cartesian potential adjacency为17,754/17,391，但
`potential_pair_adjacency_is_registered_coupling=false`且无共同物理时钟。

power跨split事件schedule逐行核对通过；三个模拟事件实际持续57/216/289小时，对应构建策略排除的整块
范围为96/240/312小时。该缺口是frozen margin unavailable，不声称上游source未观测。workload完整块未覆盖
training 816–820及holdout 1,637–1,641；training-peak normalization逐行Decimal恒等通过，holdout有6小时/
3 blocks的raw fraction大于1，maximum为1.070370705271957780430251624，未clip。

当前仍缺dispatched grid、共同clock、absolute workload power、观测flexibility/call/recovery bounds、
业务event/energy/debt合同、accounting period与deadline/checkpoint/recoverability。缺失表示未来协议尚未绑定，
不排除用户另行授权机制假设，但本轮没有选值。故`raw_chronology_candidate_available=true`仅限各margin包内，
`full_joint_service_continuation_ready=false`、`continuous_scientific_protocol_registered=false`及全部
formal/result/claim/security gates继续关闭。

机器包
`results/tables/rq2_joint_deliverability_continuation_availability_v1_non_authoritative/`的summary/chains
SHA-256为`faba770bf8f3d83229f840fc1074939742e847bd55ab793b63264cb2322dd45e`/
`0f661707d4ebb6ceb6f12073e6426a03b542322324df8a4f99b6d229ced8fc48`。下一步是形成完整versioned
continuous科学协议并接受fresh独立R4 review，不是运行planner、V7或formal。

## 2026-09-12 Google公开数据适用性与重建门

PowerData获取不是blocker：57域、mapping及既有day-0提取均在本地，本轮0下载、0付费查询。当前blocker是
数据合同语义与可复现性：官方Power PDF和notebook对`bad_*` flag方向冲突；legacy day-0按共同epoch确定
存在10分钟错位；当前Windows重建因约15位浮点字符串末位差异fail closed（`1 failed, 9 passed`），
canonical/source bytes未漂移且核心aggregate未变。上述证据不等于raw损坏或科学结果改变，但已推翻
legacy day-0“同步配对已验证”和“当前环境逐字节可重建”的解释。

故`google_power_source_integrity_verified=true`仅限source bytes；
`google_cluster_day0_temporal_alignment_verified=false`、
`google_cluster_day0_reproducible_in_current_environment=false`、
`google_power_quality_flag_semantics_resolved=false`、
`google_continuous_successor_model_input_ready=false`。如用户授权后继修复，versioned successor须按共同
epoch/interval overlap修复时间窗并冻结确定性算术/序列化；Google仍只作CPU—PDU external robustness，不提供absolute MW、
flexibility、deadline或recovery。continuous/full M6/formal/result/claim/security gates均不变。完整证据见
`docs/model_spec/google_public_data_suitability_audit_v1.md`。

## 2026-09-12 Google 23小时完整区间 successor 诊断

新增独立`DRAFT_NONAUTHORITATIVE`路径，从锁定CPU小时源与PowerData legacy窗口机械求最大完整raw-hour
交集`[3600s,86400s)`；相对正式trace起点为00:50–23:50。它使用CPU source hours 1–23和276个五分钟
Power样本，排除CPU hour 0与前/后10/2个Power样本，不拆分、插值或平移小时CPU。pair/summary SHA-256为
`54d664f2fa261413c1dfb5c05479d6aa6977e74ea8a6f36c3a5f41dba79f5930`/
`e7d6edad6f2e5abf4ad07b096b2c6c584156532fbfea452648ce78d07b551d53`。

本门仅更新为`google_cluster_23h_alignment_diagnostic_available=true`和
`google_cluster_23h_cross_process_reproducible=true`。`google_cluster_complete_24h_pair_available=false`、
`google_power_quality_flag_semantics_resolved=false`、`population_is_complete_pdu_workload=false`、
`google_continuous_successor_model_input_ready=false`保持；priority/capacity未重建，legacy逐字节重建失败未隐藏。
新路径focused为`11 passed in 1.26s`，相关green回归`14 passed in 14.19s`；legacy独立为
`1 failed, 6 passed in 0.66s`。零solver/查询/下载，不生成production manifest、lease、PASS或正式结论。

## 2026-09-12 Google 23小时描述性关联诊断

锁定第7节23小时pair并使用全部23行、零flag筛选。CPU lower/upper每小时各为14个
`collection_type × priority_tier` source strata的NCU总端点；与measured PDU归一化小时功率的Pearson分别为
`0.962184945123159126/0.962184943013110584`，平均秩Spearman均为`0.962450592885375494`。两组是端点
描述性分析，不是相关系数上下界。CPU missing overlap为0；conflict overlap总计109、涉及22小时；原276个
power样本flag未过滤，quality方向仍unknown。

机器summary SHA-256为`030626393f2ac96fcfd91f151017ad8b7c5bafa3476dd1daf67a3b500e8e23e2`，绑定上一轮
pair/summary/config/implementation与本轮实现。focused+alignment为`23 passed in 1.06s`，独立review无新增
finding。仅置`google_cluster_23h_descriptive_association_available=true`；population、24h/multiday、MW、
quality、flexibility、deadline、recovery、continuous model、formal/result/claim/security gates不变。

## 2026-09-12 Google/Zeus 有界公开数据补充

实际新增Google cell-f完整machine-events JSON/Parquet、5个schema和一个usage Parquet pilot，以及Zeus固定
commit的训练与四GPU功率小表，共38,044,870 bytes（含metadata）。cell-f全JSON约964.6 GiB、全Parquet约
429.9 GiB，超出本轮为控制资源自行采用的1 GiB下载范围（非用户预算）和当时磁盘余量，未扩大全量下载。
临时DuckDB读取因无编译工具链失败后停止；
Parquet仅绑定generation/MD5/SHA和`PAR1` magic，usage schema/row/time/continuity保持unknown。

Google machine JSON为49,603行/12,201机；716条首次ADD缺capacity且稍后UPDATE，缺口不补零或填充；
`missing_data_reason`字段全缺省。pdu17 time-zero snapshot为1221台、normalized CPU 1220.5，不是物理/MW或
完整人口。Zeus训练表3,759行，`target_epoch=nan`849行只作未解释sentinel；63配置中6个少于4 distinct runs。
四GPU功率表每配置单次测量，不能作生产PDU时序或Alibaba观测映射。

summary SHA-256为`472a2809807e0bdc10934a99dab3b6064c88f89add0945afd5917efe7a789334`，focused
`6 passed in 2.46s`。新增状态只限machine chronology与controlled-training hardware evidence；Google usage/
capacity completeness、multiday、absolute MW、flexibility、deadline、recovery、continuous model以及全部
formal/result/claim/security gates保持关闭。

## 2026-09-12 Google/Zeus 全月公开数据准备状态

`public_compute_multiday_v1_non_authoritative`已生成三项可复用但非模型输入的数据：508,896行全57域五分钟
功率原值与原flag、744行PDU17 normalized capacity小时积分、1,609行Zeus四GPU受控功率/性能。
machine-events JSON/Parquet 49,603行逐行等价；PDU17状态转换合法，72个active capacity缺口合
117.081411 machine-seconds并保持unknown。公开Google DR网页给出17:00–21:00实际调用窗口，CICS摘要给出
日内容量保持/日内完成的系统设计边界，但二者均不关闭2019 cell-f或Alibaba逐job deadline/recovery/budget门。

8个分散usage footer样本的16个row group均不可按全月/PDU17范围剪除，六列压缩外推约71.916 GB；该probe
不等于全对象证明，完整PDU17 CPU仍未提取。实现/summary SHA-256为
`92c727c4c2a275295ebf85039523e5ddc5ade599984f1c7333ce9ca6adbf42a0`/
`d3349e6b00cbd77c5b83f98bc208b90ff62612f1c2f185e1aade847970f18562`；focused/独立复核分别为
`11 passed in 29.77s`/`11 passed in 22.60s`。因此只新增
`google_power_unfiltered_multiday_prepared=true`、`google_pdu17_normalized_capacity_integral_prepared=true`、
`zeus_four_gpu_performance_prepared=true`；`google_complete_pdu17_multiday_cpu_prepared=false`以及quality、
population、MW、flexibility、deadline、recovery、continuous model、formal/result/claim/security均保持false。

## 2026-09-12 Google PDU17 全月 CPU 获取状态

用户授权按量查询和本任务累计1 TiB上限后，固定作业
`google_pdu17_multiday_v1_5f0ddc384afe27ac`已完成。dry-run/实际processed均为554,760,728,186 bytes，
实际billed为554,761,715,712 bytes，低于600,000,000,000-byte单作业上限；两个验证作业均为零计费。
公共7.7B行usage原始表仍在BigQuery，本地只保存10,416行小时网格与1行审计。共同raw窗口为
`[600000000,2679000000000)`，共744小时、2种collection type和7个priority tier；source snapshot、
query hash、参数、固定job ID、费用与本地manifest均已绑定。

审计保留55,947个exact-duplicate value groups、6,659个CPU-conflict usage groups、67,327,137个
synthesized-priority groups和21个unknown-priority groups；硬质量项均为0，PDU17映射机器数为1,295。
这些结果关闭`google_pdu17_multiday_hourly_cpu_acquisition_available=true`，并取代本register此前
“完整PDU17 CPU仍未提取”的时间点状态；不把root usage解释为完整PDU业务人口，也不把normalized CPU解释为
物理核或MW。PowerData的`bad_*`语义、全月CPU—power适配、真实flexibility/deadline/recovery/budget、
continuous model以及formal/result/claim/security gates仍未关闭。

本地包位于`data/raw/google_power_workload_2019/multiday_v1_non_authoritative/`。config/SQL/implementation/
records/metadata SHA-256分别为`594a32c8c708796ded88682bcc8e3b059ef44d246d0778d1c072dc37a69f5b3a`/
`5f0ddc384afe27accbd568830d70b924f850aea20527486e92f2f69e76d8a742`/
`91bffda376d5ec6a3b78af59b8d825b1db7df2936510f0dcea6102f4cabbde56`/
`3c204c39cc099fb344a663801e2977adcc063ab988de465e8069a62ccd987ca0`/
`557e75d553a781bb556e5b1e1a972d36302790197f3bd90a0be562a525573a57`；相关回归`52 passed in 24.08s`。

## 2026-09-12 Google PDU17 744小时未过滤同钟配对

新增独立`google_power_workload_multiday_pair_v1_non_authoritative`，仅连接已绑定本地CPU、PowerData和
capacity工件，零query、零下载、零solver。744个raw-clock小时各有14个CPU source strata、12个连续五分钟
power样本的Decimal mean与原flag计数，以及同key的capacity/unknown字段。31个24小时coverage block均从
raw trace起点划分，不解释为自然日，不作train/holdout选择。

8928个PDU17 power样本未筛选，flag组合`00/01/10/11`为6621/2307/0/0；production flag涉及194小时。
CPU conflict overlap涉及711小时，missing overlap涉及0小时，unknown tier有usage涉及21小时。capacity unknown
涉及16小时、合117.081411 machine-seconds。源CPU审计中的55,947个exact-duplicate value groups、6,659个
CPU-conflict groups、67,327,137个synthesized-priority groups和21个unknown-priority groups原样保留。
这些非零诊断意味着该包不能解释成无数据缺陷、完整PDU人口或quality-eligible pair。

aligned/summary SHA-256为`ca196505690a1b744bba2e2d689d751f454d30fb0f97856ce4d43587201380fd`/
`40fdb668b21a5d9392df1bfd32a2603e76d01be2d3c44ef11d8d11c38f032eda`；focused与相关回归分别为
`8 passed in 6.54s`/`37 passed in 46.92s`。仅置
`google_pdu17_multiday_unfiltered_cpu_power_capacity_alignment_available=true`；quality、population、MW、
headroom、flexibility、deadline、recovery、continuous model、formal/result/claim/security gates保持false。

## 2026-09-12 RQ2 本地公开数据统一交付状态

`rq2_public_data_delivery_v1_non_authoritative`已把当前scope内12个既有公开/派生数据包统一登记为catalog、
双轴field dictionary、input status和可离线验证/流式读取的交付入口。所有package/manifest/summary/primary
文件、schema和行数均逐字节绑定；Google另提供744小时扁平投影和31个raw-origin block索引。交付保持空字段
为`None`、数值CSV为原字符串，并保留Alibaba workload的6条raw>1值、Google未决flag和capacity unknown。

机器状态为`DRAFT_NONAUTHORITATIVE_LOCAL_DATA_DELIVERY_COMPLETE`，summary SHA-256为
`53b898e30d807b3b532cfaed78de20fdb0653fa53817f65fcc5a6a5d78483586`；focused为`15 passed in 43.28s`。
本步未发query、下载或solver调用，也未新增split或cross-source coupling。它只关闭
`local_delivery_catalog_available`、`offline_validation_and_loading_available`及本地软件交付scope；20项
业务/恢复输入仍为`null`，6项科学协议仍未注册。`full_rq2_experiment_input_ready=false`、
`continuous_model_input_ready=false`、`formal_result=false`、`paper_claim=false`、`security_certified=false`。

## 2026-09-12 连续多日服务 DRAFT 开发证据

新增`rq2_continuous_multiday_service_v1`协议草案、20项参数证据表和48小时合成joint-correct动作回放。
复用既有boundary组件，跨chunk保留事件、duration/rest、count、energy、debt与身份；显式检查共享调用、
服务功率平衡以及business/CFE-compatible双侧恢复头寸。解析prefix oracle和分块等价测试用于验证机制实现，
不把合成参数或初始零状态转成真实观测，也不把给定动作失败解释为数学不可行。

本草案明确采用单一nonrolling period；不支持period切换。deadline、tail、新split、cross-source coupling和
raw>1模型映射仍待注册；逐笔deadline需要债务age ledger。四臂planner、B6共享执行、完整holdout与正式服务合同
尚未由该小组件实现。`continuous_service_protocol_registered`及原有continuous/full-input/formal/result/claim/security
状态全部保持false。本次只增加开发证据，不关闭科学blocker。

可审阅入口：`docs/model_spec/rq2_continuous_multiday_service_v1.md`、
`docs/model_spec/rq2_continuous_multiday_parameter_evidence_v1.md`和
`docs/model_spec/rq2_continuous_multiday_validation_v1.md`。保留全部旧冻结协议与结果，未清理仓库、下载或启动正式实验。
相关旧v5回归的symlink测试在创建fixture时遇到Windows `WinError 1314`；该分支尚未验证，须在具备symlink权限的环境重跑。
未修改冻结测试或放宽验收，本轮不声明完整PRE_SEAL验收完成。

## 连续恢复债务 cohort deadline 开发证据

新增DRAFT cohort账，按产生小时/假设到期小时携带余额与永久到期短缺。
合成测试用于验证跨日守恒、晚恢复保留违规和unknown/right-censoring区分，并对照既有aggregate债务递推。
详情见`docs/model_spec/rq2_continuous_debt_cohorts_v1.md`。该组件不提供真实deadline来源、恢复功率可行性、
自动分配策略或四臂controller；known deadline仅为mechanism_assumption，真实输入仍null。
连续科学协议、full-input、formal/result/claim/security各门均不变；旧冻结字节及结果保留。

## 连续四臂物理/cohort绑定开发证据

新增非权威四臂显式动作适配器，提供B6分离规划动作的共享物理重放；分离成功不推断共享成功。
物理恢复与cohort allocation逐时守恒，状态按arm/mode/track、轨迹/时钟、envelope与period绑定；
保留逾期记录，拒绝跨轨串账和planning历史替换。详见`docs/model_spec/rq2_continuous_four_arm_replay_v1.md`。
这里的物理校验仅为归一化数据中心服务功率与业务包络，不涉及电网dispatch/AC/N-1或最优性证明。
真实deadline、非零carry-in适配、异质逐服务deadline、因果策略与正式四臂planner仍未完成；
全部正式协议/输入/结果/claim/security门保持关闭，旧冻结协议和结果继续保留。

## 2026-09-13 固定因果恢复规则的前缀开发证据

新增单current-observation策略接口与不可变接受/拒绝记录，固定known EDF/unknown FIFO恢复机制，
调用请求保持完整，B6共享执行失败不重优化。首次失败停留在最后已提交的物理/cohort状态，
汇总明确分开submitted、accepted和rejected小时，并保留既有deadline miss/unknown/censoring状态。
详见`docs/model_spec/rq2_continuous_causal_policy_v1.md`。该开发证明固定规则的因果前缀回放行为，
不证明其他策略不可行、完整连续holdout风险或真实业务违约率。
失败小时后的实际服务动作和债务递推、非零carry-in、异质deadline及真实参数来源仍未完成；
正式科学协议、full-input、formal/result/claim/security门全部保持关闭。
开发与独立复核的六文件回归均为182项通过；三项审查实现问题已修复，当前无开放实现finding。
此状态只覆盖合成固定策略前缀，不关闭上述科学输入及完整轨迹blocker。

## 2026-09-13 前缀诊断交付开发证据

`rq2_continuous_prefix_diagnostics_v1`将固定策略的六个合成场景和四臂回放持久化为可重放诊断包。
输入均为mechanism_assumption；真实观测未用于填补业务deadline、恢复参数或carry-in。
接受/拒绝/未提交小时、规划候选/已提交状态、unknown/逾期/截尾分别保留，拒绝后实际轨迹仍为未评价。
文档入口为`docs/model_spec/rq2_continuous_prefix_diagnostics_v1.md`；此本地交付不关闭真实参数或完整失败轨迹blocker，
continuous-service/full-input/formal/result/claim/security各门保持原状态。
本地包已生成且完整重放匹配（24组合、1038记录）；独立最终相关回归194项通过。该软件交付证据不改变上述科学门。

## 2026-09-13 拒绝后实际动作合同的开发边界

`rq2_continuous_actual_action_contract_v1`已明确显式assumed实际动作与原规划拒绝的区分，
提供同一原观测/约束下的共享物理-cohort后继校验。迟到恢复、unknown和缺失实际动作分别保留；
网络/CFE完整请求无法履行时仍未评价，未引入削减硬请求或额外救援资源。
这补齐了“已给定合法机制动作”的递推接口，尚未补齐实际动作选择的因果规则、B6后继完整policy、
真实运行证据或所有失效类型的实际轨迹。旧B6 planning不恢复，原拒绝结果不改写。
详见`docs/model_spec/rq2_continuous_actual_action_contract_v1.md`；正式协议/full-input/formal/result/claim/security门保持原状态。
主线程和独立最终相关回归均216项通过，当前无开放实现finding；这仅完成显式机制动作递推开发，不关闭动作选择与真实轨迹blocker。

## 2026-09-13 固定因果补救机制开发

`rq2_continuous_recovery_controller_v1`为已支持的physical/shared拒绝固定当前小时共享恢复规则及组合策略身份，
从原拒绝小时开始永久走共享物理账。该模块补齐一个明确机制的动作选择，不声称覆盖全部拒绝类型或真实运行政策。
B6后继与旧分离策略结果单独标识；输入/decision/planning拒绝及完整请求仍无法实现的小时保持未评价。
未来输入扰动与跨chunk一致性用于开发非预见性验证；真实输入揭示时序、参数、非零carry-in、损失模型、正式split及经验风险仍缺证据。
详见`docs/model_spec/rq2_continuous_recovery_controller_v1.md`；全部正式科学与运行门保持原状态。
该固定机制controller已通过开发与独立最终九文件回归（均244项），当前无开放实现finding；此证据不关闭未覆盖失效类型和真实运行风险blocker。

## 2026-09-13 组合策略后继交付证据

`rq2_continuous_composite_diagnostics_v1`将primary/补救/未评价各段持久化，八个合成场景共32个场景与臂组合。
原拒绝与补救不重复计算小时；来源fault的raw hour独立于输入序号和已验证服务时钟。
本项保留未评价小时及后缀，不转成真实服务风险或B6原策略效果；真实参数、非零carry-in、未覆盖失效类型与正式split/coupling仍缺证据。
详见`docs/model_spec/rq2_continuous_composite_diagnostics_v1.md`；正式协议/full-input/formal/result/claim/security门不变。
本地包已生成且离线重放一致，独立最终相关回归257项通过；raw-source字段歧义已修复。此交付不关闭上述科学输入或未覆盖实际动作blocker。

## 2026-09-16 连续机制拒绝覆盖核对

三套既有公开/前缀/组合交付只读核验通过，当前开发产物无需重复生成。新增拒绝覆盖矩阵见
`docs/model_spec/rq2_continuous_rejection_coverage_v1.md`；primary policy_decision阶段补充5项合成测试，
相关四文件回归68项通过，验证拒绝不推进shared/planning状态、不激活补救且不允许消费后缀。
既有input/separate-planning拒绝仍不属于实际后继入口；B6 separate-planning拒绝后的共享动作及独立policy合同
是下一开发缺口。此核对没有新设实际失效行为或改变任何trigger、阈值与正式门禁。
20项实证参数null、6项协议未注册、四臂非零carry-in及未覆盖实际动作blocker保持；底层aggregate carry-in
小例已存在，不应重复宣称未开发。正式科学/输入/运行/result/claim/security门均保持原状态。

## 2026-09-16 formal-ready关键路径与网侧连续性缺口

依据用户持续推进到可开始正式实验的目标，完成只读科学关键路径审计，决策包为
`docs/plan/RQ2_连续正式实验决策与验收_v1.md`。B6 separate-planning后fallback不是主容量定义的前置，
暂不扩展；当前优先完整continuous科学协议、输入与planner。

旧grid v4配置为`free_boundary_24h_normal_state_SCUC`，`_process_block`逐块调用normal prescreen，
prescreen使用`fixed_initial=None`；无active outage块未求normal generation/commitment。
因此旧1071块即使全部发布，也不单独证明跨块UC/generation/ramp/min-up/down连续性。
这不是已发现具体旧解违反ramp，而是缺少所需保证；旧具名benchmark结论保持原范围。
解除continuous网侧门需要注册连续dispatch合同并提供跨边界状态/初态与全小时约束证据，不能直接拼接旧自由边界结果。

开放观察末端只给prefix证据，完整恢复服务的容量UB仍需要延续/closure见证；期限、accounting、
coupling、raw>1映射与风险分母等科学决策待明确。未知不能填0或解释为完整服务成功。
已提交用户选择是否接受有明确机制假设的区间/unresolved正式结果；问题未答时不代选验收口径。
独立零solver机组carry审计草案已新增，见`docs/model_spec/rq2_continuous_grid_carry_v1.md`；
它只验证给定committable轨迹的局部bounds/ramp/dwell，不关闭上述网侧、科学或formal门。
主线程相关回归116项通过；独立pre-seal targeted/相关回归25/75项通过，8,000状态组合与20,052分块重放无差异，
未发现开放局部实现finding。旧科学v5/implementation v2/execution v3的5/14/22个inner成员hash均匹配。
该证据只完成机组chronology审计组件的DRAFT验证，不是完整continuous grid生成、输入验签或official审查。

## 2026-09-16 用户指定拒绝语义补缺后的推进

用户明确先补缺项、优先梳理尚未覆盖拒绝类型及实际动作语义。上条“暂不扩展fallback”的开发顺序
由此更新；正式科学选择仍待注册，但不阻止独立机制合同的开发与短验证。
新增B6分离规划拒绝后的独立固定共享后继，见`rq2_continuous_b6_planning_recovery_v1.md`。
原拒绝与规划保持归档；同一小时从最后已提交共享状态尝试完整请求，失败不推进，成功后永久共享执行。
18项针对性测试通过；最终相关8文件167项通过，旧三个冻结包41个成员哈希匹配。
独立pre-seal审查完成：另8文件228项回归及125组恢复cap枚举通过，限定范围无阻塞实现finding。
这是一项mechanism_assumption开发产物，不提供真实故障处置证据或原B6容量结果。
剩余输入/决策错误、完整请求无法满足时的实际服务/损失合同、非零carry-in、多period与正式planner等继续开放。

## 2026-09-16 显式部分响应与请求短缺分账

已核对既有formulation及v4 holdout，确认永久drop不是未满足调用，主实验默认drop=0。
新增`rq2_continuous_partial_response_v1.md`和显式动作核算接口，保留原请求/拒绝，按执行量递推债务。
grid短缺candidate不提交且禁止后缀；grid足额/CFE不足可提交局部机制状态并明确CFE failure。
37项新测试覆盖功率/债务/包络、来源与表示故障、deadline、原容差及历史链；主线程相关186项通过。
独立pre-seal数值finding已修复并复核，fresh相关186项通过；正式组合/导出须保留原观测与投影角色的外层记录绑定。
最终只读pre-seal审查限定范围无开放实现finding，另四臂20组枚举无提交/债务/failure分类差异。
本项不包含自动fallback、完整因果策略、永久损失或网络安全认证，所有formal/result/security门保持。
下一缺口是为已明确动作合同建立完整事前策略及训练容量/可用柔性绑定，并补minimum-event-power、响应/ramp等完整包络。

## 2026-09-16 连续固定容量动作策略开发

新增`capacity_policy.py`与薄`aggregate_response.py`，见`rq2_continuous_capacity_policy_v1.md`。
事前固定声明容量、min-event、up-ramp/response及最大恢复功率；逐小时读取当前可用柔性，精确选择grid→CFE响应，
inactive时复用既有EDF恢复。原始请求与Fraction执行投影分别保留；grid短缺candidate-only停止；无hour23 reset。
51项新增测试及主线程248项相关回归通过，设计与实现pre-seal审查finding均闭合。
独立审查另有321项连续模型测试、39,256组Fraction枚举、四臂恢复4例与10个policy身份变体通过。
当前容量为mechanism_assumption，training_capacity_certificate=null；旧24h D_a不直接成为开放连续training证书。
后续还需continuous training产物闭包、原观测/投影的正式导出绑定、累计shortfall/删失汇总及完整科学协议与planner。

## 2026-09-16 容量策略诊断开发

新增`rq2_continuous_capacity_diagnostics_v1.md`对应导出器，复用旧prefix输入和Fraction编码。
原请求/可用柔性、派生投影、业务候选与提交状态分别保留；累计短缺含容差内小量，候选与提交分账。
cohort仅按最后提交账本评价；来源错误、未提交后缀与完整服务结果保持未知。
15项新诊断测试与5文件91项相关回归通过；独立pre-seal依赖闭包finding已修复并复核，限定范围无开放finding。
36个case-arms/1091条记录已发布到新的non_authoritative诊断目录，verify-existing完整重放一致。
formal training、真实输入闭包和风险定义仍未完成；本地交付不提供正式容量或经验风险结论。
下一项为同一policy/split/trace/period的已验证前缀持久化交接：由canonical zero origin重放证明
非零物理/cohort状态来源，不接受裸snapshot、不重做已有chunk推进、不将training末态接holdout。
任意非零初态分布、rolling reset、正式burn-in/scoring和closure仍依赖科学协议。

## 2026-09-16 已验证前缀状态交接开发

新增`prefix_handoff.py`，规格见`rq2_continuous_prefix_handoff_v1.md`。由接收方独立提供摘要与canonical zero origin，
只从完整已提交原始前缀重放恢复cursor；不直接导入裸物理/cohort snapshot。spec/策略/双时钟/来源/period不变，
精确动作、执行投影、终态、deadline历史和运行代码依赖均校验。现有初始化、推进和旧诊断包不修改。
45项新测试通过（含全新Python进程恢复）；最终7文件195项相关回归通过；独立pre-seal限定范围无开放finding，
独立复核45项targeted及全部连续模型381项测试通过。旧capacity诊断包36组/1091条完整重放一致。
这是derived mechanism state持久化，不是observed carry-in、任意初态分布、正式burn-in或training容量证书。
下一主线核查continuous四臂training planner可复用kernel及24h/terminal限制；完整服务closure仍须科学协议。

## 2026-09-16 continuous planner关键路径核查

只读领域核查定位`src/rq2_joint_deliverability_v2/model.py::build_arm_planning_model`：kernel按输入向量长度构建，
但旧输入schema固定24h，模型固定zero initial、末小时inactive，并施加terminal debt上限（旧协议为0），且尚无逐cohort deadline。
旧`structural_recovery_witness`依赖末端清债，不能直接用于开放末端。

新增需显式处理的行动集差异：旧planner允许grid响应超过有效请求以满足minimum-event-power，
新continuous capacity policy限制served不超过原请求。两者不能直接混用成同一training-policy证书。
旧training也使用scenario-separable、可见未来的离线追索，只共享D；不是现有固定因果策略的训练证书。

下一可开发对象为独立DRAFT开放前缀离线容量规划kernel：显式行动模式、共同H/same nonrolling period、
四臂共享/分离账、cohort恢复与已观察deadline。先做解析小例和约束构建，保留旧sealed实现。
该对象提供prefix容量证据；仅当证明它是同一完整服务对象的必要投影/松弛时，才可传递有效prefix LB。
prefix可行解/UB不构成complete UB，后者保持null/unresolved；不据此生成完整四臂归因。
正式行动集、因果policy class、输入支持/权重/窗口和closure仍须科学协议明确后验收。
具体无默认模式、集合包含门与最小验收见`rq2_continuous_planner_contract_v1.md`。

## 2026-09-16 continuous planner内核开发

新增独立`continuous_planner.py`：任意共同H的build-only Pyomo模型、显式行动/离线信息模式、training源连续性、
zero/single-period/open-terminal、四臂shared/B6分离账、逐cohort有效能量分配及due-hour恢复后的硬期限约束。
58项解析构模测试及6文件193项相关回归通过；未调用solver，领域与实现pre-seal限定范围无开放finding。
独立复核58项targeted及全部连续模型439项通过；恢复集合术语finding已修复，旧capacity诊断36组/1091条重放一致。
minimum-event须大于原活动容差、输入限1h built-in数值；这些是开发接口限制，不改正式阈值。
模型恢复显式标识为continuous_nonnegative_recovery_relaxation，未完成物理effective recovery及causal量化桥接；不能直接视为因果策略行动集。
精确duration/rest离散规则进入identity/evidence；GRID_EXCESS仅旧service方程，不等于旧sealed完整模型。
所有prefix/complete容量证书字段保持null。下一步仍需独立逐时incumbent witness与solver证据适配，
并在明确projection关系前保持完整对象LB/UB与四臂归因unresolved。

## 2026-09-16 连续规划逐时动作见证开发

新增`planner_witness.py`，规格见`rq2_continuous_planner_witness_v1.md`。完整有序场景/小时候选绑定planner identity，
以Fraction独立核验调用/恢复包络和分配守恒，再复用物理/cohort账；保留原始请求、执行投影与失败候选。
已知deadline在到期小时恢复后验收，失败不推进已接受状态；B6通过仅属于分离规划。
独立pre-seal发现ramp预计算系数与逐时精确乘积的边界差异，已绑定canonical模型实际系数并补反例；
41项针对性测试及7文件234项相关回归通过（1.56s），独立复核限定范围无开放finding。
审查方另复跑41项targeted及planner/witness合计99项通过；修复前479项全连续回归不冒充最终snapshot全回归。
源码SHA256为`88664772c4d4a7006cae835b05de4dc80a998e048d58e36e2bb8fb5600478f78`，
测试SHA256为`7529670a455fc98daf092912d44ef3f0300e8f52faec3d34a31ce5e1b4e2ef4d`。
主线程另完成324组四臂两小时无恢复赋值对照，witness与模型约束检查一致；初次枚举fixture误给零义务deadline被拒绝，修正fixture后通过。
solver原变量残差/整数性及bound适配尚未完成，全部容量界与因果训练证书仍null；本项未调用solver。
下一项复用旧solver配置/版本/规模工具，独立重建canonical模型审计赋值，不能沿用旧24h完成期证书。

## 2026-09-16 连续规划赋值审计开发

新增`planner_assignment.py`，规格见`rq2_continuous_planner_assignment_v1.md`。从全部变量保存原数值/表示与错误，
用调用方可信inputs/arm重建canonical模型，分别核验变量界、整数性和全部原约束残差；提取Fraction动作复用逐时见证。
当前提交结构摘要覆盖域/界、约束、目标及active状态，不能冒充solver实际输入来源证明。
raw solver outcome保留status/termination/bounds及失败原因，绑定assignment身份；全部仍unaudited/unresolved。
独立pre-seal发现公开审计对象可重标及整数容差>=.5使验收失效，已加构造时canonical快照重算和整数容差适用性门。
47项新测试及8文件281项相关回归通过（2.12s）；两项finding已由独立pre-seal复核闭合，限定范围无开放finding。
审查方另复跑47项targeted及planner/witness/assignment共146项通过，原重标攻击与半整数门反例均被拒绝。
源码SHA256：`4e1a7fdc991accb61e613d79d8a3f958362bd1cf022e590dc66642f9388296b6`；
测试SHA256：`59992c8d93483893fc7f5464dac542336df61ef48cc9eb5db0b9f78138cac396`。
只读版本查询为Pyomo 6.10.1、HiGHS 1.15.1、Gurobi 13.0.2；不作为新模型规模/许可证门通过证据。
模块与单元测试不调用solver；另做4次H=2手工机制接口探测，HiGHS单线程、各限1秒，规模23变量/47约束（B6为41/88）。
四臂raw optimal容量依次.25/.125/.375/.25，1个solution、canonical最大约束残差0，精确见证通过；报告仍raw/unresolved，
该探测发生在审计对象重算修复前，不冒充最终组件或正式规模验收。下一项是独占build→solve→snapshot的短合成适配与真实solver证据绑定。

## 2026-09-16 连续规划短求解流程开发

新增`planner_short_solve.py`，规格见`rq2_continuous_planner_short_solve_v1.md`。内部fresh build、显式短预算、
一次version-checked native solve、完整solver/problem/solution记录检查、原生label/变量解析、显式load及canonical/精确见证审计。
前后结构/options/version、加载前初值与native/loaded变量一致性均进入证据；timeout候选可审计但区间保持未决。
独立pre-seal先后指出solution status一致性、runner contract身份、native多记录inventory及过大容差导致负UB问题，
均已添加限制与反例，另补problem目标数与native objective一致性。独立pre-seal限定范围无开放finding。
最终72项targeted及9文件353项相关回归通过（3.49s），独立方另复跑72项通过（1.51s），均包含4个真实
HiGHS 1.15.1 H=2/每次1秒小例，尚不作正式规模验收。
源码SHA256：`566c05a85df84b7b33c1e8e60aa589aaf2f1760b16be8b0a3fc6a4651627ee23`；
测试SHA256：`145ad7dbbce1cd5e18a1598908169bd7ecc8ffbfb09e8d1e54feb6040951b276`。
仅在完整门通过时提供声明数值容差下的development relaxed-prefix solver区间；effective见证单列，
physical prefix区间、complete/causal/infeasibility证书仍null，formal/security仍false。无生产seal/lease或正式运行。

## 2026-09-16 下一主线：连续normal网侧构模缺口

只读领域核查确认`rts_gmlc_scuc._build_context/_build_model`按len(points)构造，可由新DRAFT入口复用；
旧`_validate_inputs`限制H<=24，旧normal prescreen强制free initial，不修改这些已存在入口与冻结依赖。
旧fixed_initial虽连接首小时commitment/ramp，却未使用time_in_state_hours约束初始残余minimum-up/down，
旧audit亦未覆盖。现`grid_carry`已用ceil(raw minimum)和严格非负integer age审计，因此新normal薄层须补
R=max(ceil(minimum)-age,0)个未来同态小时；fractional age非法，不静默改合同。
下一实现：新连续输入验证→复用旧纯context/model核心→附加residual dwell→由accepted末小时轨迹回放得到terminal carry。
`_derive_initial_state`取第0小时并人为设置age，不可用作末态；normal baseline需覆盖无事故小时。
normal-only不能冒充现`validate_chronological_dispatch`要求normal加contingency的全安全结果。
逐小时corrective LP若后续复用，需保留原事件seed/start/end，不能证明事故态跨小时ramp；其正式语义仍待科学协议。
以上尚是定位与实现入口，未生成continuous grid、未关闭输入或网络安全门。

## 2026-09-16 连续normal构模与末态见证开发

新增`continuous_grid_normal.py`，见`rq2_continuous_grid_normal_v1.md`：连续来源索引/时钟与完整初态绑定，
复用旧SCUC纯核心，附加initial residual minimum-up/down，独立canonical全变量审计后回放末态GridCarry。
normal基线覆盖无事故小时；保留发电、AC/DC flow、reserve、功率平衡和成本约束。
末端不重置开停义务；同一输入摘要覆盖数据、初态、机组carry、时钟声明及代码依赖。
最终六文件325项相关回归通过（16.19s）；新组件82项targeted经独立复核通过（14.06s）。
128组三小时开停轨迹与独立carry核验一致。已有RTS源25h build-only产生22,275变量/28,004约束，未调用solver；
仅合成2h用1线程/1秒HiGHS做开发测试。旧SCUC和chronological_dispatch无diff。
独立pre-seal的结果重标、业务边界、摘要类型、角色类型和依赖闭包finding均已修复复核；限定范围无开放finding。
本条不提供输入已发布、完整安全或formal-ready证据。下一项为owned normal短执行产物与事故响应连接器：
normal先于事件求解，保留全小时baseline、原事件seed/id/start/end及1-based到zero-based显式映射。
事故态跨小时语义、完整输入、科学协议及正式规模门仍开放；逐小时corrective不冒充跨小时安全轨迹。

## 2026-09-16 连续normal短执行与事故连接开发

新增`continuous_grid_candidate.py`，规格见`rq2_continuous_grid_candidate_v1.md`。owned fresh normal短求解，
完整native记录/变量映射、显式load与fresh canonical赋值审计后，保留全小时baseline并逐小时连接原事件corrective LP。
事件保留原seed/id/start/end，明确1-based source_hour到zero-based事件索引；无事故小时仍保存normal调度。
候选保留normal与corrective完整赋值，native省略fixed或完全unused无界连续变量时仅作显式canonical completion；
used变量缺失、timeout、异常及不合格bound均未决。精确版本限定的HiGHS不可行报告只用于fresh zero-DC确认，
双报告标签为`solver_reported_exogenous_infeasibility`，数学不可行证书仍null。
最终44项targeted通过（8.76s），五文件270项相关回归通过（23.09s）；独立pre-seal另复核44项通过（8.70s），
限定范围未发现开放finding。四个真实H1/2/3微例包括20 MW正grid need，每例中的各次solver调用限1秒/1线程。
未运行真实RTS多日求解，未发布production manifest或continuous输入包；旧normal与corrective源码保持。
事故态跨小时ramp/开停/修复回接尚不由该逐小时连接器证明，完整连续安全与formal门继续开放。

## 2026-09-16 多小时事故态约束内核

新增`outage_trajectory.py`，规格见`rq2_outage_trajectory_v1.md`。共同horizon下建立实际出力、拓扑、
节点平衡及跨小时ramp；normal commitment固定，forced trip仅豁免故障机组下降ramp，repair逐原event显式限额。
actual origin与normal carry分离；源起点stationary-down不伪造新trip，中途首小时repair核对原事件与实际前态。
目标明确为fixed curtailment vector可行性或正权重总削减，均为offline full-event-path机制问题。
27项targeted通过（9.42s）；最后两项测试补充前四文件176项相关回归通过（26.62s），源码随后未变。
独立pre-seal当前27项通过（9.11s）；前序小时界与计数文档已同步并完成最终复核，限定范围无开放finding。
fresh import闭包精确匹配；旧SCUC/corrective与solver adapter无本轮修改。新事故态LP仅构模及解析赋值。
下一项为完整事故态赋值审计、独立实际轨迹见证与实际末态交接，再接owned短求解；不能直接复用旧标量curtailment结果验收。
repair数值、因果响应信息结构及grid_need estimand尚未注册，完整continuous输入与formal门仍开放。

## 2026-09-16 事故态赋值见证与同轨迹实际交接

新增`outage_assignment.py`及`rq2_outage_assignment_v1.md`，fresh重建完整事故态模型，分别审核原赋值fixed值、
变量界、全部约束及目标有限性；同一完整problem/assignment下按绝对小时提取实际末态，normal carry单列回放。
每次交接重审全赋值并精确核对前缀末态，不提供suffix重优化或通用新窗口origin导入。
独立pre-seal发现运行时contract/容差漂移能改变旧ID或验收，已改为见证捕获并在入口拒绝漂移，补两项反例。
修复后五文件211项相关回归通过（52.98s），包含33项新测试；独立复跑33项通过（25.11s），运行时合同finding已闭合，限定范围无开放实质finding。
当前只证明固定1e-6下的给定离线赋值可行性，solver来源/最优bound/唯一grid_need/因果性均不由本组件证明。
下一项是事故态owned短求解与native/load/canonical证据连接；正式完整输入、科学及执行门保持未完成。

## 2026-09-16 多小时事故态短求解连接

新增`outage_short_solve.py`，规格见`rq2_outage_short_solve_v1.md`。内部构模、规模预算、一次native求解、
完整原生记录/变量与canonical completion、显式load及独立完整赋值审计已连接；结构/options/version前后核对。
weighted模式只给当前offline标量目标的开发区间，fixed-vector模式只给可行赋值见证；物理见证与solver lineage分列。
五次真实H2/3事故LP微求解各限1秒/1线程，含c=(20,20)、w=(2,3)、目标100，以及同固定向量目标0不输出调用界。
40项targeted通过（25.46s），六文件251项相关回归通过（76.57s），独立pre-seal另复跑40项通过（25.85s），限定范围无开放实质finding。
无解/timeout/错误只保留原始证据；不继承旧corrective的HiGHS不可行兼容认证，infeasibility certificate仍null。
本组件未发布正式grid_need包、未建立因果调用或业务容量证书。下一主线核对业务实际功率/恢复与连续网侧可行域的连接，
并保持主estimand、机制参数、完整输入、正式规模与执行门开放。

### 下一接口缺口：业务动作和恢复后的实际节点负荷

源码核对：`outage_trajectory.py`的节点负荷为`dc_requested_mw[t]-curtailment[t]`，其curtailment是净减载MW；
`continuous_planner.py`的service power为`workload_occupancy-track_call+recovery`。前者没有后者的业务债务、
grid/CFE分账或recovery变量，后者没有连续事故网络方程。两边各自通过不能证明组合实际功率可由网络交付。
因此禁止将当前weighted/fixed事故解自动命名为外生grid_need后直接发布正式下游包。
下一最小开发是显式固定业务动作轨迹的联合物理检查：用已声明MW映射得到实际DC功率，把该功率送入事故节点平衡，
分别复核业务轨迹和连续网络赋值；首版不优化业务动作、不替用户选择grid_need向量或放宽完整硬请求。
MW归一化基准、grid/CFE调用归属、事故向量的等式/下界/内生语义和网侧受限时恢复规则须显式合同，
未注册部分保持机制/未决；这一接口补缺不授权正式输入生成或改变旧冻结结果。

## 2026-09-16 固定业务实际功率与连续网侧联合赋值

新增`business_grid.py`，规格见`rq2_business_grid_v1.md`。重放完整已提交CapacityPolicyCursor并核对预存digest，
以显式decimal MW单位线性映射baseline/grid/CFE/recovery/actual，精确核对baseline及physical/connected界。
新prescribed-load模型保留事故generation/response/ramp/repair/topology，用实际业务功率替换节点负荷；旧模型源码不改。
canonical审计外另用原exact MW和Fraction计算节点平衡，均用1e-6，不以投影误差放宽门槛。
服务适用性/原请求/shortfall与网络赋值分列；CFE-only不获grid履约证书，B6仅验证共享实际执行；完整恢复/因果网侧证书仍null。
最终37项targeted通过（20.88s），六文件193项相关回归通过（53.05s），独立pre-seal37项通过（20.61s），限定范围无开放实质finding。
覆盖recovery>baseline、无事故CFE减载、业务合法但网络ramp失败、generator trip/repair和支路故障约束保留。
映射、配对和origin仍是机制假设，不提供经验风险或完整履约认证。下一项是固定动作的owned短网络可行性求解，
然后才可按科学合同准备完整连续输入；正式数据/协议/规模/运行门保持未完成。

## 2026-09-16 固定业务动作网络短求解接口

新增`business_grid_short_solve.py`，详见`rq2_business_grid_short_solve_v1.md`。复用既有native/加载/canonical
流程，对固定完整业务动作运行一次显式短预算LP，再用原exact MW独立审核节点平衡。
最终37项新测试随六文件236项相关回归通过（115.12s）；独立pre-seal发现的矛盾solver termination误标
lineage已修复，独立8项status测试通过（12.09s），限定范围无开放实质finding。
真实3h恢复例取得网络赋值，4 MW/h ramp例保持unresolved，CFE短缺未被网络成功掩盖；所有证书仍null。
本组件不生成因果grid_need或完整服务容量。正式continuous输入、训练容量/策略绑定、完整恢复及科学/执行门继续开放。

下一上游缺口为因果网侧请求的信息合同：当前完整未来事故路径和完整业务轨迹只能提供offline见证。
已整理`rq2_causal_grid_request_contract_v1.md`的逐小时可见信息、actual状态、请求/动作/调度顺序与前缀不变性验收。
请求的净减载/独立义务含义、CFE credit、事件/修复揭示时点、dispatch选择与失败处理尚未注册；
这些选择不能从测试fixture或当前offline区间代入。合同草案未实现generator或改变formal门。

## 2026-09-16 当前事故揭示输入开发

`simulate_n_minus_one_events`的raw event ID含seed，事件end还可能是horizon截断；直接交给策略会暴露未来信息，
截断末端不能证明repair。新增`event_disclosure.py`与`rq2_event_disclosure_v1.md`，以显式完整当前N-1
outage overlay机制推进揭示状态；initial-down onset未知、只用本地序号，repair cap仅在当前返回报告出现。
36项新测试随63项相关回归通过（1.54s）；独立pre-seal的公开state伪造历史finding已修复并复核闭合，
独立36项通过（1.50s），限定范围无开放实质finding。
normal计划仍含未来source/身份，完整请求链不因此因果。
该模块无solver、无grid_need或dispatch、无正式输入发布；科学/数据/规模/运行门继续保持。

## 2026-09-16 正常计划与当前网络条件隔离开发

新增`grid_information.py`及规格`rq2_grid_information_v1.md`，审计侧重验完整normal赋值，策略侧仅投影
当前计划/上小时planned commitment、静态物理参数和独立当前报告。allowed身份不继承原source/seed摘要。
36项新测试随四文件179项相关回归通过（16.36s），独立pre-seal另复跑36项通过（3.60s），限定范围无开放实质finding。
给定完整assignment通过不证明选择过程未看未来，origin前发布时间仍是机制声明；receipt/确定性normal选择规则未完成。
当前request/dispatch、真实来源、完整服务和formal门未关闭。
继承限制：旧SCUC区域无备用资格机组时构模失败，新入口明确不产view；若后续源输入出现该情况，需backend successor修复后再推进依赖工作。

## 2026-09-19 当前小时实际网络状态验收开发

新增`current_grid_step.py`及`rq2_current_grid_step_v1.md`，连接隔离当前信息、当前事故揭示、prior actual carry与固定exact MW业务功率。
包含当前节点平衡、normal response、actual ramp、trip/repair及完整赋值/Fraction审计；无有效赋值时不产生next carry。
最终41项针对性测试通过（8.86s），修复后五文件173项相关回归通过（50.01s）。
独立pre-seal发现fixed机组current bounds歧义已修复；独立41项通过（8.49s），限定范围无开放实质finding。
当前没有solver入口、请求/dispatch选择、因果或完整服务证书。
基础availability变化没有额外trip/repair合同，入口停止；当前修复cap、origin与normal事前信息仍是机制输入。
下一项接owned当前小时短求解。科学/完整continuous输入/规模/正式执行门保持未完成。

## 2026-09-19 当前小时网络短求解开发

新增`current_grid_short_solve.py`，规格见`rq2_current_grid_short_solve_v1.md`。复用既有native/显式load/canonical流程，
单次预算内求解后fresh exact审计；physical见证、solver来源与owned carry分别记录。来源异常不发布本result的next carry。
最终37项针对性测试通过（14.28s），五文件193项回归通过（79.22s，最后两项新增前，源码未变）；
独立pre-seal当前37项通过（13.97s），限定范围无开放实质finding。真实微求解每次1秒/1线程，无正式输出。
当前请求生成与dispatch选择仍缺，不能从零目标任意可行解推导固定因果策略。已核对减少DC负荷可能违反下降ramp，
标量完整调用不替代实际功率网络校验，见`rq2_causal_grid_request_contract_v1.md`新增机制反例。
下一项为共同参考请求与各臂actual carry的自包含设计，保留原四臂估计对象。完整恢复、输入与正式运行门保持开放。

具体设计候选已写入`rq2_common_reference_request_design_v1.md`，包括共同reference LP、数值selector、各臂双提交和单位分辨率拒绝。
该页不是正式选择；CFE-only的物理验收是否进入D_C、reference定义、全小时调用范围、selector/容差与实时reserve仍须新科学协议明确。

## 2026-09-19 共同参考 LP 与赋值审计开发

新增`reference_grid.py`，规格见`rq2_reference_grid_v1.md`。共同reference origin为显式反事实机制，不能直接传入arm actual carry；
继承current-step物理约束，以P_ref∈[0,B]变量最小化B-P_ref。完整赋值以exact P重建fixed-power核独立审计。
44项targeted通过（16.41s），修复后五文件193项相关回归通过（39.15s，最后远端节点例新增前，源码相同）。
独立pre-seal发现expected_identity类型可被自定义相等绕过，已加严格SHA256门及10个反例，独立43项通过（17.13s），finding闭合。
限定范围无开放实质finding；模型已有非单调功率域、repair/outage及远端节点解析证据，但尚未求得/发布最小请求或reference后继。
下一项为总预算约束下的数值selector及reference状态递推，再接共同请求适配与逐臂事务；完整科学/输入/正式运行门保持开放。

## 2026-09-19 共同参考数值selector与跨小时状态开发

`reference_selector.py`实现G、真实L1偏差与逐UID generation的数值词典序选择，
`reference_grid.py`扩展受控ReferenceGridState；各级要求owned optimal、finite bounds/gap和fresh物理/目标审计，
全部通过才提供所选exact请求和末态。完整n+2调用及最大模型规模在首次solve前检验，策略身份禁止中途变更。
52项targeted通过（56.94s），四文件174项相关回归通过（105.29s）。独立pre-seal发现原1e-6锁定门
可接受超过声明gap的目标漂移，已改必填lock_tolerance_mw<=absolute_gap_mw并按实际L1复算；
独立52项通过（58.80s），finding闭合，限定范围无开放实质finding，见`rq2_reference_selector_v1.md`。
当前仅开发短预算，20次调用硬上限对应最多18个机组UID，不等于正式规模可用。
下一必要工作为各臂fixed-power actual selector，再接exact共同请求适配与业务/网络双提交；
完整来源、训练容量与策略绑定、完整恢复、正式科学协议及运行门继续未完成。无新正式结果或证书。

## 2026-09-19 固定实际功率数值dispatch选择

新增`actual_dispatch_selector.py`，固定PrescribedDcPower，按真实L1偏差及sorted UID generation选择。
ActualDispatchOrigin即绑定selector/solver/预算/runtime/source policy；跨小时受控state继续绑定，
raw/reference状态不能作为actual selector前态。每级owned optimal、finite bounds/gap、fresh物理与Q目标锁定审计，
全部通过才发布候选末态，result显式保存exact功率，见`rq2_actual_dispatch_selector_v1.md`。
46项targeted通过（36.65s），五文件220项相关回归通过（140.85s）；独立46项通过（38.99s），
限定pre-seal无开放实质finding。旧reference及当前网络核/短求解源码保持，git diff --check通过。
本组件最多19个generator UID；不是正式RTS规模接口，也不提供业务/网络双提交或四臂身份绑定。
下一项为共同请求exact单位适配，再连接各臂业务candidate与网侧候选的原子提交、失败保留和跨chunk递推。
正式来源、训练容量绑定、完整恢复/right-censoring、科学协议与运行门保持未完成。

## 2026-09-19 共同请求精确单位适配开发

新增`common_request_adapter.py`，复用既有Fraction业务路径，G/U原样进入共同JOINT/shared hour。
显式canonical decimal U绑定workload normalization身份，exact occupancy*U必须与reference baseline相等；
仅接受完整owned selected reference。正请求被旧活动阈值消去或分离/合计活动不一致时保留原值并unresolved，
不归零、不上调。独立pre-seal发现原正例跨training/holdout与outage seed仍被接受，已新增审计侧
RequestSourceAudit：完整normal input与prepared绑定、重建current view，并严格匹配business split/seed/hour。
修复后38项targeted通过（18.06s），六文件223项相关回归通过（116.46s）；独立38项通过（21.88s），
来源finding闭合，限定范围无开放实质finding；直接digest依赖与60模块fresh-import闭包也已核对。
详见`rq2_common_request_adapter_v1.md`。1/3请求经四臂债务及prefix导入导出保持精确；prefix本身不证明reference来源。
下一项仍是共同mapping/ref身份的跨小时固定与业务/网络双提交，不能仅把业务成功cursor当成网侧已提交。
正式连续输入、训练容量与固定策略绑定、完整恢复及科学/运行门保持未完成；没有正式证书或结果。


## 2026-09-20 小时事务验证与下一步

共同小时与业务/网络双状态事务已完成DRAFT开发，见`docs/model_spec/rq2_hourly_transaction_v1.md`。
共同请求未完成不填0；业务拒绝不调用网侧求解；网络输入拒绝或求解未完成保留候选证据，两侧已提交状态均不推进。
CFE-only物理检查与grid服务义务分别记账。独立pre-seal发现的共同发布前实现身份重验缺口已修复并复核闭合。
修复后22项针对性通过（27.43s），独立22项通过（27.26s），八文件291项相关回归通过（128.23s，exit 0）。
下一项为四臂连续运行协调：公平初态与固定策略核验、唯一公共链、整段预算、完整证据持久化与重放。
当前仅为内存事务；训练容量绑定、正式规模、连续输入、完整恢复/right-censoring及科学/正式运行门仍未完成。


## 2026-09-20 四臂连续小时协调开发

`episode_coordinator.py`已连接单对象内存中的四臂共同请求链、固定策略、公平物理/业务初态、整窗最坏预算预检和逐小时预留。
保留各臂独立停止；末小时保留恢复债务，窗口消费完不代表完整履约。完整小时输入、候选、外层提交、已开始/未完成/未开始臂分别记录。
`hourly_transaction.py`同步区分dispatch执行异常与求解前网络输入拒绝，缺失执行结果不猜零调用。
独立pre-seal 31项episode（44.69s）及23项hourly（32.10s）通过，findings闭合；九文件323项相关回归通过（170.08s，exit 0）。
完整合同、开发hash和命令见`docs/model_spec/rq2_episode_coordinator_v1.md`；旧22/291项记录保留为此前版本证据。
下一项为完整episode证据的持久化及无solver重放，再处理跨进程唯一性/恢复；现有业务prefix不能替代reference→mapping→business→actual全链。
本组件仍为DRAFT_NONAUTHORITATIVE。完整连续输入、训练容量与四臂策略绑定、正式规模、恢复/right-censoring及科学/正式运行门未关闭。
所有初态与未识别业务参数保持机制声明；没有新增真实运行观测、正式结果、容量/安全认证或formal-run authority。


## 2026-09-20 完整episode重放的原生证据前置核

新增`grid_evidence_replay.py`，保存原生求解记录并相对于独立提供的canonical模型重算结构、原生赋值、completion、残差、目标、状态与bound投影。
不从JSON直接制造owned求解结果或可执行cursor；缺失原生记录保留partial/unresolved。报告显式model_relative_only，未验证来源/selector chain及外部builder效果。
58项针对性通过（20.58s），独立58项通过（20.15s）；修复后六文件276项相关回归通过（122.60s，exit 0），限定pre-seal findings闭合。
详细合同、命令和hash见`docs/model_spec/rq2_grid_evidence_replay_v1.md`。现有episode、hourly transaction与两个selector源码未改。
下一项先接reference/actual专用stage及选择链重审，再完成全episode归档、无solver重放和跨进程恢复；当前不能声明完整episode持久化已完成。
本轮新增的是机制开发证据，非真实运行观测；完整连续输入、训练容量、恢复/right-censoring、正式规模和科学/正式运行门保持开放。


## 2026-09-20 Reference/actual选择链来源绑定重放

`selector_replay.py`已实现独立输入/policy绑定、逐级canonical模型重建、目标锁定/物理重审及完整结果身份比对；公开接口只返回诊断。
完整拒绝与partial中断分别记账；partial只验证此前prefix，不产生所选末态或恢复游标。
独立pre-seal发现partial单级及总调用数可联动改小，现按capture阶段绑定调用数并拒绝create与post-call证据混存。
修复后100项targeted通过（78.41s），独立100项通过（79.66s），finding闭合；七文件348项相关回归通过（223.48s，exit 0）。
合同、命令与开发hash见`docs/model_spec/rq2_selector_replay_v1.md`。现有episode/hourly/两类selector及原生重放核源码保持。
下一项为全episode来源绑定归档与无solver重放，连接mapping、业务动作与实际功率、预算预留及外层提交；随后验收跨进程唯一性与安全恢复。
本组件仍为DRAFT_NONAUTHORITATIVE；没有新增真实观测、正式结果或认证。完整连续输入、训练容量与策略绑定、正式规模、恢复/right-censoring及科学/运行门仍未完成。


## 2026-09-20 完整返回episode归档与来源绑定重放

`episode_replay.py`已连接独立初态/逐小时输入、reference选择链、共同映射、四臂业务动作至exact实际功率、actual选择链及外层提交的无solver重放。
完整返回链逐字段比对；partial只报告证据可达prefix，真实actual gap之后可保留未验证后缀；外层中断必须回滚且保留预留。
缺返回不能冒充合法成功或零调用；重审同小时已返回臂并核known/unknown调用及started/skipped/incomplete/unattempted库存。
最终39项targeted通过（170.63s），独立39项通过（176.58s）；限定pre-seal findings闭合。
四文件192项相关回归通过（289.75s），对应最后interrupted-error非空门和相同依赖清单提取之前的直接前驱；最终局部变更由39项完整targeted覆盖，未重跑同范围broad。
合同、精确hash与命令见`docs/model_spec/rq2_episode_replay_v1.md`。原selector重放、hourly transaction与episode coordinator源码保持。
下一必要工作为跨进程唯一执行、持久化提交及安全恢复，包含尚缺invocation journal的in-flight边界；当前不提供可执行恢复游标。
本组件仍为DRAFT_NONAUTHORITATIVE；完整数据、训练容量/固定策略绑定、正式规模、恢复/right-censoring及科学/运行门保持开放。无新真实观测、正式结果或证书。


## 2026-09-20 本地事务日志与开发恢复

`episode_store.py`已接入同一规范NTFS目录内的合作进程排他、SQLite intent/result事务、完整来源重放后的开发续跑。
调用前commit并重新打开核intent；已有intent但无result保持unknown并禁止重跑，结果commit响应丢失通过inspect与外部保留head对账。
每个新archive须延续此前已提交的exact历史和前态；复制目录、schema/源/提交链漂移、reparse/hardlink与不完整初始化均拒绝。
独立31项targeted通过（360.92s），同一最终字节三文件101项相关回归通过（562.22s，exit 0），限定pre-seal findings闭合。
覆盖真实进程竞争、五个os._exit崩溃窗、提交异常、NTFS路径及历史改写反例；进程退出测试不等于断电硬件认证。
`episode_replay._verify`现在私有返回诊断及完整重建snapshot，公开wrapper仍只返回诊断；最新source/hash与完整命令见`docs/model_spec/rq2_episode_store_v1.md`，旧验证历史保留。
本组件仍为DRAFT_NONAUTHORITATIVE，仅沿用120调用/60秒短预算；没有生产lease、正式运行授权或新真实观测。
下一必要工作为正式网络规模与continuous输入适配的仓库核查/开发；完整数据、训练容量/固定策略绑定、恢复/right-censoring及科学/运行门保持开放。


## 2026-09-20 真实RTS来源与连续选择器规模核查

本地RTS-GMLC固定manifest及25条源文件校验通过：73母线、120 AC支路、1 DC支路、158机组、8784连续小时。
当前完整UID词典序reference需160次/小时，actual每臂159次，四臂整链796次/小时；168小时预留133728次。
这超出现有单selector 20次、episode整窗120次/60秒开发上限；是准入规模差距，不是运行失败或不可行证据。
新增create-only库存机器记录及源码绑定，详见`docs/model_spec/rq2_continuous_source_scale_audit_v1.md`；没有solver或正式运行。
独立只读核查确认旧源小时zero-based、新continuous one-based；旧free-boundary不能直接作为continuous incoming carry。
既有真实H=25构模计数仅找到文字记录，缺输入/初态绑定的可重算机器产物；不重复开发normal/current/episode核心。
下一步补真实来源组装与build-only证据，并审查158 UID规模下的执行合同；不直接放宽旧预算或替换词典序目标。
完整连续输入、训练容量绑定、恢复/right-censoring及科学/正式运行门仍开放。


## 2026-09-20 真实来源适配与H=25构模机器证据

新增source_normal薄层，将固定RTS文件manifest、显式request/initial/carry和zero/one-based小时映射绑定；不推定初态或认证split/trajectory。
真实H=25 build-only已落盘完整输入与依赖：22275变量/28004约束、solver_calls=0。此前只有文字计数的缺口现有可重算开发记录。
此例使用热机全关/零出力/min-down age机制初态，未证明前序网络可行性，不能作为已发布normal plan或正式数据输入。
24项source适配测试与normal/grid-information相关回归共142项通过（17.06s）；产物hash/时钟/映射/非认证flags核验通过。
合同、命令、最终产物及源码hash见`docs/model_spec/rq2_source_normal_v1.md`。旧冻结文件和开发中间记录均保留。
剩余真实输入义务包括power-block来源/split/trajectory映射及normal assignment；158 UID选择器规模、训练容量、完整恢复与科学/正式运行门仍开放。

独立pre-seal最终复跑24项通过（2.04s），限定范围findings闭合；最终构模JSON与runner/adapter/计数模块及40个依赖源码hash独立核验匹配。详细证据见`rq2_source_normal_v1.md`，无official gate变化。


## 2026-09-20 公开边缘连续窗口提取

新增source_window，复用已有continuation审计，按显式split/raw起点/长度及power seed提取唯一连续chain窗口，保留原始CSV值及训练归一化依据。
真实power seed20260822的holdout链从4440开始；split边界4392周边排除小时不能补造。workload holdout继续使用training peak，>1值不裁剪。
四份独立25h power/workload training/holdout样例已create-only落盘并从源重建逐字段一致；不声明同钟或已注册coupling，不生成可执行episode。
三文件64项相关测试通过（4.39s），已有输出覆盖尝试exit2且hash不变，diff检查通过。合同/命令/产物hash见`docs/model_spec/rq2_source_window_v1.md`。
下一项连接power窗口身份到normal assembly/carry，再按登记机制处理workload功率映射。真实normal assignment、158 UID执行规模、训练容量、恢复及科学/正式运行门保持开放。

公开来源窗口独立pre-seal完成：同范围64项通过（4.42s），四份记录完整来源重建及身份hash独立匹配，限定范围无开放实质finding；正式门不变。


## 2026-09-20 电力窗口与normal来源绑定

新增power_normal_binding，从外部assembly/window/config身份重建两端并核split、seed、trajectory、raw/continuous小时、timestamp、系统负荷及RTS源manifest。
真实25小时来源对应已落盘：最大系统负荷差0.0 MW，solver_calls=0。CLI预审发现的现场身份自比较已修为必填外部expected assembly pin，首次派生记录保留。
五文件164项回归通过（18.81s），产物身份/源码hash/时钟与非认证flags核验通过。详见`docs/model_spec/rq2_power_normal_binding_v1.md`。
本层只证明来源对应；初态仍为机制声明，未证明前序网络可行、normal赋值或事故dispatch。
下一项为workload→业务功率机制映射与coupling合同；真实normal assignment、158 UID执行规模、训练容量、完整恢复与科学/正式运行门仍开放。

电力窗口/normal绑定独立pre-seal最终18项通过（1.56s），外部pin finding闭合，最终产物/core/test/runner hash核验一致；限定范围无开放实质代码finding，正式门不变。


## 2026-09-20 workload数值投影与精确功率接口

核查真实1632小时：普通float(raw)*250在training599/816、holdout592/810个in-range小时不满足CommonRequestMapping精确十进制恒等式；精确十进制乘积再投float对应553/543，报告分开公式和计数。
新增显式half-even数值投影，保留raw与有符号误差；不放宽旧接口，不自动clip。250MW/12dp仅为开发声明，816training+810holdout投影后精确等式成立，6个holdout原>1保持unresolved。
四文件97项回归通过（14.36s），含独立Decimal全1632行oracle；source-bound checked诊断重新生成与落盘逐字段一致，diff检查通过。
详细合同、命令、最终hash与中间记录边界见`docs/model_spec/rq2_workload_projection_v1.md`。原数据和旧协议保持。
正式精度/功率映射与raw>1策略尚未注册；CFE/coupling、业务恢复合同、真实normal赋值、执行规模及正式门继续开放。

workload数值投影独立pre-seal最终19项通过（0.22s），两项findings闭合；全源精确等式/误差/6项超界及两类计数独立复算一致，最终产物与源码hash匹配。正式门不变。


## 2026-09-20 独立来源显式配对与CFE请求暂存

新增source_pair，外部pin重建同split的power/workload独立窗口，显式relative-offset机制配对；normalization绑定原训练来源、投影/功率规则。
复用完整既有CFE target缺口公式，不乘occupancy或截断请求；grid0明示待reference填写的空槽。两个raw时钟分别+1保留各自前边界，不声称同钟。
任一小时projection未解决则顶层hours=null，全部诊断行保留。training25h正例staged，holdout1190..1214含5个超界的25h例unresolved。
两份DRAFT声明和create-only诊断已从源完整重建相等；五文件114项相关测试通过（17.06s），hash与diff检查通过。见`docs/model_spec/rq2_source_pair_v1.md`。
下一项绑定pair动态baseline到normal request；旧常量250MW构模例不能替代。真实normal赋值、规模执行、训练容量、恢复与正式coupling/科学门仍开放。

source_pair独立pre-seal三文件54项通过（5.46s），两份JSON/声明/pair identity及实现hash匹配，限定范围无开放实质finding；114项broad采用主线程证据，正式门不变。


## 2026-09-20 配对动态baseline与normal输入

新增pair_normal_binding，外部pair/assembly身份重建后复用power来源核查，逐小时精确校验normal DC baseline=pair投影MW=occupancy*U；私有快照隔离caller变更，未解决pair在网络来源前拒绝。
真实H25先derive候选身份，再用外部保留pin verify并构模，22275变量/28004约束、solver_calls=0；动态baseline为0.0093335315–0.02631222675MW，原250常量声明保留。
该范围是所选开发窗口/线性机制结果，不是功率标定、正式代表样本或履约证据。两阶段完整输入与pair逐小时等式已核验。
五文件152项回归通过（17.84s），模式/pin/产物hash及diff检查通过。详见`docs/model_spec/rq2_pair_normal_binding_v1.md`。
下一项需合法normal赋值及current连接；H25变量与158 UID selector调用数仍超既有短预算，正式规模合同与科学/运行门保持开放。

动态normal绑定独立pre-seal限定范围无开放实质finding，最终两阶段产物/身份/输入/模式flags复核一致；独立44项对应新增2项CLI测试前库存，最终152项由主线程覆盖。正式门不变。


## 2026-09-20 连续真实规模执行合同草案

新增`docs/model_spec/rq2_continuous_scale_execution_contract_v1.md`，把前置normal、逐小时reference/actual与完整任务资源分开。
代码核查确认episode预留不含normal及构模/审计/归档；solver TimeLimit总和不等于wall-clock、内存或存储上限。
保留158 UID选择语义时H25四臂预留19900次，加一次normal为19901次；这是完整路径计数，不是实测耗时或成功保证。
下一实现明确为normal-only后继入口：外部输入/规模/资源pin、完整原生证据、normal.optimal及无错witness后才接prepared/current。
草案列出规模、求解与进程时间、RSS/存储、许可/pilot、未知调用及六步验收义务；不扩展旧GridDevelopmentBudget或EpisodeBudget。
本轮只有文档设计及源码/产物hash/计数核对，没有solver、代码行为变更或正式门变化；所有后续实现/真实规模pilot证据仍待补齐。


## 2026-09-20 独立normal短执行内核

新增`normal_execution.py`及规格`docs/model_spec/rq2_normal_execution_v1.md`，实现外部input/execution/实际scale绑定的单次normal执行，复用原canonical模型和原生证据核心。
保留normal.optimal且完整witness无错的接受门；可行但未最优、资源超限及返回后身份漂移保留证据并拒绝接受，缺raw的中断调用数保持unknown。
新预算独立于旧GridDevelopmentBudget，旧selector/episode上限不变。资源记录为同步observed wall、Windows进程生命周期peak working set及core数值payload大小；不是强制终止或完整归档门。
结果明确hard_resource_limits_enforced=false、durable_invocation_tracking=false、public_source_binding_verified=false；完整结果identity绑定raw/witness、资源及错误字段。
当前只推进了normal-only内核，真实来源接入、独立进程/持久化监督、完整归档资源验收及真实规模normal验证仍待补齐；正式实验门保持开放。

独立normal内核最终四文件216项回归通过（41.52s），独立54项targeted通过（18.54s）；完整result identity与core字节命名两项pre-seal findings闭合。
最终source/test hash与命令见`docs/model_spec/rq2_normal_execution_v1.md`；旧candidate/episode源码hash保持，diff及新文件空白检查通过。该证据仅支持tiny同步内核，正式门不变。


## 2026-09-20 公开来源与normal执行连接

新增`source_normal_execution.py`与规格`docs/model_spec/rq2_source_normal_execution_v1.md`，把已核验assembly/pair动态baseline接入独立normal内核，前后从源重建绑定。
连接层独立核assembly/pair/binding/input/kernel/source execution外部pins，重算绑定内容摘要；检查内核成功标志与raw/witness/调用/状态一致。
post-source失败保留内核证据并拒绝外层接受；无完整内核返回仍记调用数unknown。来源报告以不可变JSON保存，完整返回有内容identity。
此层仍无独立进程/持久化intent/完整归档资源监督；旧kernel及来源适配源码保持。真实H25用来源重建测试在kernel边界停止，没有真实RTS求解。
下一步先核查已有transport_v5所属子进程监控和episode_store事务日志的复用适用性，旧冻结资源阈值/receipt/授权不继承；再补normal监督与真实规模验证。

来源连接层最终独立覆盖32项（31项17.65s及真实H25来源边界1项103.14s，均exit0），主线程相关五文件124项通过（24.17s）。
assembly/pair直接pin、绑定正文摘要及内核成功证据一致性findings闭合；最终hash/命令见`docs/model_spec/rq2_source_normal_execution_v1.md`。
H25仅完成来源连接验证，数值内核在测试边界停止；没有真实网络normal赋值或正式运行，监督/持久化/真实规模/科学门继续开放。


## 2026-09-20 Normal一次性开发调用日志与监督复用核查

新增`normal_store.py`，复用旧episode的NTFS路径/文件身份/合作进程排他原语，独立normal schema绑定完整运行请求和源码。
intent经SQLite DELETE/FULL事务提交并重新连接读回后才调用source-normal；已有intent禁止重试。完整encoded result及identity有独立字节门、提交与读回。
重开可用外部genesis/current head核对丢失返回；只提供returned_record_unreplayed诊断，不恢复owned游标、不认证native来源或数值结果。
原normal/kernel/source执行模块及旧episode存储源码保持；当前仍为同步执行，真实RTS求解与正式门未变化。
独立复用核查确认旧transport_v4/v5缺明确HANDLE ABI、存在PID二次打开窗口且没有父死亡保护；这些原语不能直接继承到新normal监督器。
下一项为显式wintypes、同一保留HANDLE及Job/释放握手的normal进程监督，再补完整资源/结果重放验收；旧冻结阈值、源和结果保留。详见`docs/model_spec/rq2_normal_store_v1.md`。

Normal日志最终独立19项通过（26.06s），相关55项通过/1项未重复H25（55.94s）。create/head模式finding闭合，四个os._exit窗、跨进程排他、readback/提交响应丢失及完整record门有开发证据。
最终source/test hash和命令见`docs/model_spec/rq2_normal_store_v1.md`；旧episode_store及source execution hash保持，diff通过。独立进程监督/父死亡保护、数值replay、真实规模和正式门继续开放。


## 2026-09-20 Normal 开发子进程所有权原语

新增`normal_process.py`与`docs/model_spec/rq2_normal_process_v1.md`，使用显式WinAPI ABI和创建时JOB_LIST绑定，持有同一process HANDLE，挂起核查后单次释放；Job非继承且kill-on-close，提供每进程commit门与短时deadline终止。
真实短子进程测试覆盖父死亡三个窗口、异常退出、后代终止、内存分配拒绝、旁观进程不受影响及创建后中断句柄回收；没有solver或真实电网求解。相关process+store回归41项通过（27.47s）。
这只完成监督链底层所有权原语，尚未连接normal专用worker/持久化请求与结果核对，也未补Job总内存/系统commit储备、数值重放和真实规模验证。正式门保持开放；旧冻结源、结果及未提交文件保留。


Normal进程原语独立pre-seal限定范围无开放实质代码finding；规格中崩溃窗口措辞已按实际注入位置修正。最终22项独立targeted通过（1.04s），源码与测试hash见`docs/model_spec/rq2_normal_process_v1.md`。后继worker仍须补请求/环境身份绑定、同线程或并发合同、整Job静默后读取工件以及资源/日志/数值重放验收；不能把进程原语测试升级为完整监督或正式运行通过。


## 2026-09-20 Normal worker 与一次性日志连接

新增`normal_worker.py`，已把显式输入/运行pins、受限环境、挂起Job worker与原normal_store连接：父目录排他、request及launch intent持久化、worker exclusive claim、normal intent/result日志、整Job静默后parent readback。normal_process draft补同线程校验、显式环境、Job总commit与quiesce。
worker正常退出且有完整记录仅标returned_record_unreplayed；零退出无结果、超时、中断和提交后异常退出均不升级成功，也不自动重试。下层normal_store/source execution/kernel及旧冻结transport未变。
主线程process+worker+store相关回归68项通过（57.92s），含tiny 1秒/1线程HiGHS、三类intent/result崩溃窗、worker重复claim、环境漂移及未静默禁止读结果。正例来源边界为明确synthetic stub；固定worker入口另验证真实来源缺失拒绝，未执行RTS求解。
下一项为持久化normal结果的独立数值重放；系统commit储备、父进程/整个任务资源与磁盘验收、真实规模normal/current/四臂及科学注册门仍开放。详见`docs/model_spec/rq2_normal_worker_v1.md`。本轮非正式开发，不产生seal/receipt/正式运行授权。


Normal worker连接最终相关回归69项通过（62.41s），最新24项worker独立targeted通过（34.95s）。实际argv及摘要已加入launch并由worker核对sys.orig_argv，claim/Observation绑定launch摘要；旧进程规格明确区分历史快照与当前合同。限定范围预审finding已修复；完整资源验收、独立数值replay及真实规模证据仍待补齐，详见`docs/model_spec/rq2_normal_worker_v1.md`最终验证记录。


worker监督后续补齐两项实测证据：Job合计内存160/256 MiB成对控制，以及worker已提交intent后的集成父死亡窗口。新增3 cases主线程6.57s、独立6.54s均通过；限定范围pre-seal findings闭合。它们补充此前69项相关回归，仍不构成normal数值重放、真实规模或正式门通过。最终source/test hash及精确命令见`docs/model_spec/rq2_normal_worker_v1.md`。


## 2026-09-20 Normal 保存结果独立数值重放

新增`normal_replay.py`与`docs/model_spec/rq2_normal_replay_v1.md`：以外部record/result/store/replay/input/execution pins核对持久化内容，前后重建来源绑定，固定normal模型复用既有纯数值replay核，复核赋值/目标/残差/界投影，重新计算完整normal witness并核对接受标志。store入口要求独立保留的当前结果head，不以genesis替代。
初步targeted29项通过（49.87s）。生成tiny记录后禁止solver factory、normal/source执行入口，重放无native求解；重算哈希的赋值/目标/资源/标志篡改仍不能接受。partial/timeout/缺返回保留未决状态，不恢复执行游标、不认证原生来源或最优性。
旧normal/source/kernel/store/worker/native replay源未修改。相关回归与独立预审继续核验，正式门保持开放；完整资源、真实规模normal/current/四臂、恢复/风险/科学注册仍待对应证据。


## 2026-09-20 Normal 数值重放最终开发验证

normal_replay 已补齐资源拒绝的精确计数、保存计时的 float 类型与偏序、lifetime peak 单调性、spec/budget/scale 编码类型，以及 admission/native/canonical 构模计时数量检查。保持成功标志并重算哈希的篡改反例也被拒绝；来源后检失败在来源恢复后仍保持 unresolved。
最终四文件相关回归 177 passed in 148.23s；独立 targeted 46 passed in 82.15s。限定范围 pre-seal findings 已闭合，完整命令和最终 source/test hashes 见 `docs/model_spec/rq2_normal_replay_v1.md`。旧 normal/source/store/worker/native replay 文件哈希保持。
以上支持 tiny 合成网络及显式来源 stub 的记录一致性，不认证 native 执行历史、资源测量或真实 RTS 求解，不生成 seal、receipt 或正式授权。
下一必要工作为整个 normal 任务的资源验收：父进程输入准备/归档/重放预算、系统 commit 储备、临时文件与归档磁盘边界及故障停止规则。已有 worker 的子进程 Job 限制和单条 payload 字节门不能替代这些项目；真实规模 normal/current/四臂、恢复/右删失及科学参数注册门继续开放。


## 2026-09-20 Normal 主机资源余量观测原语

新增 normal_resources.py 和 docs/model_spec/rq2_normal_resources_v1.md：固定 Windows ABI 观测系统 commit 与 caller-available 磁盘余量；明确追加需求/储备，同卷需求合计、储备取最大、采样可用空间取最小。外部 identity 绑定目录 dev/ino/volume GUID、预算与源码，前后检查；失败不返回 sufficient 报告。
相关 resources/process/store 回归 82 passed in 29.79s；独立 targeted 35 passed in 1.86s，限定范围无开放实质代码 finding。测试包括真实只读 Windows 调用和目录替换，以及模拟边界、配额可用量不足与 API 故障；没有 solver 或磁盘/内存压力运行。
本项仅补只读观测及声明比较，未接入 worker，未创建资源预留或硬配额。下一项是完整 normal 任务监督连接：内部固定调用 observer，覆盖输入准备、执行、审计、归档及重放，明确父进程与子进程预算、专用临时目录、持续观测/停止及写入失败保留规则；不能信任 caller-supplied observation。真实规模、科学注册与正式运行门保持开放，旧冻结代码、结果及未提交文件保留。


## 2026-09-20 整任务来源准备入口与监督范围核查

新增 normal_task_inputs.py 及规格 docs/model_spec/rq2_normal_task_inputs_v1.md，以有界三文件声明与独立 assembly/input/pair/binding/scale pins 重建完整来源输入；保留机制初态和 build-only 角色，实际重建 binding，前后核声明及依赖。准备结果沿用 owned construction，不能直接构造或 dataclass.replace；不形成执行授权。
最终相关回归 99 passed, 2 deselected in 21.55s；独立短测 33 passed, 1 deselected in 4.17s。最终真实 H25 来源准备单独 1 passed in 52.13s，内部准备50.381511秒，solver factory禁止调用；assembly/binding保持原固定产物身份，未重新构模或获得真实normal赋值。两项限定pre-seal findings已闭合，最终哈希/命令见规格。
监督核查确认旧worker的输入deepcopy/encode/store初始化位于Job外，replay也未纳入。既有scale execution contract已补两阶段task设计：受限execution/archive child，全Job静默后保留结果pins，再起独立replay child；尚缺task process owner、wire-level pin捕获、固定runtime reserve采样/停止、私有scratch及phase日志故障验证。旧60秒process/worker和30/60秒kernel预算保持；不得把一次准备耗时当引擎pilot或调阈值依据。正式实验门仍开放，旧冻结结果与未提交文件保留。


## 2026-09-20 Normal 整任务进程监督原语

normal_task_process.py 已实现独立任务预算、固定 host reserve 采样、deadline/资源/API/身份失败停止，以及整 Job 无活动成员和直接子进程已退出的共同确认；记录 process/Job peaks，不推断 solver 状态。运行中只比较 reserve，避免重复计入已分配需求。公开 normal_task_child contextmanager 覆盖初始化、交接和 finally 清理，直接构造拒绝。

主 targeted 34 passed in 6.78s；task process/process/resources 相关回归 97 passed in 7.81s；独立 targeted 34 passed in 5.91s。初始化前后与 base constructor 返回中断、父死亡、资源竞态等限定范围 pre-seal findings 已闭合。最终 source/test hashes 和命令见 docs/model_spec/rq2_normal_task_process_v1.md。旧 normal_process 字节与 60 秒限制保持。

本项尚未接入 phase intent、来源准备、normal execution/store 或 replay。下一项为整 Job 静默后 controller 有界读取并独立保留归档 lineage pins，再连接 execution/replay 两阶段，避免在 controller 重建完整 assembly。磁盘是采样式停止而非硬配额；完整任务故障验收、真实规模求解、四臂恢复/右删失及科学注册门继续开放。没有正式运行，旧冻结协议/结果和所有现有未提交文件保留。


## 2026-09-20 Normal 归档身份有界捕获

新增 normal_archive_capture.py 与规格 docs/model_spec/rq2_normal_archive_capture_v1.md。Controller 可在独立确认 Job 静默后，复用旧合作式 lease，在同一只读 SQLite 事务中核精确 schema/header/intent，分块哈希 opaque record，沿旧公式保留 current head 和 record SHA；result identity 仅保留 external claim，交原 replay_normal_store 核验。此入口不加载完整 assembly/赋值，不把不透明字节一致性提升为数值或 native 认证。

数据库/metadata/record/lock 有明确读取边界；残留 sidecar/reparse、来源/文件漂移、扫描/分块 deadline 和中断均拒绝返回 pins。无 result 仅 unused/unresolved_intent，不推断原生调用次数、不重试。只读指数据库连接，原 lease 仍 r+b 打开锁文件；deadline 是合作式检查，不是硬实时 I/O 保证。

capture/store/replay 相关回归 94 passed in 235.45s；之后补 lock/sidecar 边界，最终 targeted 31 passed in 30.07s，独立 targeted 31 passed in 31.66s。限定范围 pre-seal findings 闭合；最终 source/test hashes 与命令见规格。旧 normal_store、normal_replay、episode_store、normal_process 源码哈希保持，未启动真实 RTS 求解或正式实验。

下一必要工作为 compact request 与两阶段 phase controller/worker：把来源准备、normal 执行/归档放入受限 Job，持久化 intent/launch/claim，Job 静默后捕获 pins，再启动独立重放 Job。需同时补私有 scratch、父进程预算与准备/执行/结果/重放各故障窗口；claim 来源与 Job 静默不能由本 capture 返回值自证。真实规模 normal/current/四臂、完整恢复/右删失和科学注册门继续开放，旧冻结协议、结果及现有未提交文件保留。


## 2026-09-20 Normal compact request 与两阶段固定 worker

新增 normal_task_worker.py 和规格 docs/model_spec/rq2_normal_task_worker_v1.md：小型 typed request/64 KiB phase packet 不携带 assembly 或赋值，绑定来源/normal/replay pins、环境、实际模块和 Python 可执行文件。worker 验证 controller 预存 intent/launch 与实际 PID/creation FILETIME/argv/cwd/environment 后才 exclusive claim，再进入固定 prepare→旧 store execute 或重新 prepare→旧 replay 路径。完整 replay 诊断经字节门/fsync/readback 后才写 small completion；异常保留 intent/claim，不能自动重试。完成记录仍是 worker 声明，不是 controller 数值验收。

相关 task_worker/task_inputs/oldworker 回归 81 passed, 1 deselected in 170.68s；之后补准备后运行上下文复核，最终 targeted 26 passed in 78.71s，独立 targeted 26 passed in 76.31s，限定范围 pre-seal findings 闭合。测试包括显式 tiny 来源 stub 的 execute→capture→独立 replay（replay 禁止 solver），运行上下文漂移、写入失败、丢失 completion，以及真实固定 argv 挂起 Job 的缺失来源负例。真实入口短测试初始被 host commit 准入拒绝，收紧本测试 process/Job 上限后通过；不能推断真实规模资源充足。最终 hashes/命令/准确证据边界见规格，六个复用模块字节保持。

下一项是父 controller：外层排他、phase 顺序、专用 scratch、父进程/Job/磁盘预算、release 前持久化 intent/launch、Job 静默后的独立小文件与 capture/report 核验，并补各父死亡/写满/SQLite/fsync 窗口。当前尚未有完整任务 supervisor 或真实 RTS 求解，normal/current/四臂真实规模、完整恢复与右删失、科学注册及正式启动门继续开放。旧冻结协议、结果和现有未提交文件保留。


## 2026-09-20 Normal 整任务顺序 controller

新增 normal_task_controller.py 与 docs/model_spec/rq2_normal_task_controller_v1.md，连接现有 compact worker、受限 Job、opaque capture 与 numerical replay。外层 lease、专用 scratch、release 前 intent/launch、进程身份和整 Job 静默核验、独立保留 pins、完整有界报告及 replay 后第二次 capture 已接通；报告复读与 archive pins 共同检查最终归档一致性。成功持久文件仅为最终写入前验证快照；API 在最终写入/回读与 elapsed 检查后才返回开发流程完成。数值报告继续区分 accepted/unresolved/inconsistent，全部正式权限标记为 false。

资源合同保留 process/Job commit 限制、host reserve 采样、父进程 lifetime working-set 观测与有界目录盘点；没有硬磁盘配额或整任务资源认证。故障保留已有 intent/claim/store/report，不自动重试。测试使用明确 tiny synthetic 来源与真实 Windows Jobs；未修改入口的缺失来源负例另测。真实公共数据、机制参数、synthetic fault injection 分开标注。

本轮曾完成 26 项基础测试、56 项故障扩展测试；最终源码、相关回归、独立 targeted 计数与 hashes 以 controller 规格的开发验证记录为准。公共数据交付包 6 个输出绑定、复合诊断包 7 个文件哈希和 8 个复用模块源码哈希核验一致。连续多日、恢复债务、四臂及拒绝动作/诊断已有开发产物继续复用。

下一必要工作为真实来源 normal 整任务受限端到端验证，以及 normal witness 到 current/episode 的输入与时序交接；不能把 normal terminal carry 当成 incoming origin。真实规模 full-UID selectors/四臂资源、完整恢复与右删失、风险分母和科学注册/正式启动门仍开放。本次不变更旧冻结协议或结果，不清理现有未提交文件。


Controller 最终验证补记：相关回归 186 passed in 289.44s；最终单时钟判定修复后定向 5 passed, 56 deselected in 27.79s；独立最终 targeted 61 passed in 133.65s。首次定向复测遇到实时 host commit 余量拒绝，原预算重跑通过，详情见规格。限定范围 pre-seal findings 闭合，不关闭真实规模、整任务资源或正式门。最终 source/test hashes 见 docs/model_spec/rq2_normal_task_controller_v1.md。


## 2026-09-21 真实来源 H25 整任务首次短验证与诊断缺口

已新增固定开发声明 configs/rq2_normal_task_h25_development_v1.DRAFT.yaml 与薄入口 experiments/audit_rq2_normal_task_v1.py；入口默认只读，显式开发调用绑定 exact YAML/script SHA。主/独立声明测试均7项通过；沿用原机制输入，固定HiGHS单次1秒/1线程，Job/process各768 MiB，未扩展科学或正式预算。

首次实际调用已终态，controller为unresolved_task_attempt/execute，25.562秒；子进程exit1，整Job静默true。仅保留request/intent/launch/claim及观测，没有normal store/completion/capture/replay。process/Job峰值接近声明cap，runtime host reserve没有拒绝；但无child traceback，不能认定具体异常/limit触发，也不能推断solver_calls=0或数学不可行。此次不重试、不换root、不放宽预算。完整22工件hash索引在 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/summary.json，合同和日志位置见 docs/model_spec/rq2_normal_task_h25_development_v1.md。

当前下一必要工作已收敛为独立零solver来源准备诊断：同source pins和768 MiB上限，记录prepare/assembly/binding阶段与有界异常栈，先区分来源准备失败与后续执行失败。诊断不会追认原attempt确切异常。normal真实来源成功、current/episode交接、四臂/恢复/右删失、资源与科学注册/正式启动门继续开放。旧冻结协议/结果、已有未提交文件和失败attempt全部保留。


## 2026-09-21 来源准备探针定位身份编码 MemoryError

独立零solver prepare probe已执行一次并终态；保持原source-request pin与768 MiB process/Job cap，117秒phase+3秒quiet。实际11.016秒exit1、Jobquiet=true，无host reserve/API error；保留阶段before_prepare→source_assembly_enter，捕获本次probe的MemoryError，栈为continuous_grid_normal.normal_input_identity→_digest→_encode。详见 docs/model_spec/rq2_normal_task_h25_development_v1.md 及 results/tables/rq2_normal_prepare_probe1_non_authoritative/probe.summary.json。13项新probe证据另存prepare_probe1_evidence.json；原attempt1及22项hash均保持。此结果不追认attempt1异常，不认证cap唯一因果或数学不可行。

据此新增独立identity_stream.py原语，流式处理dataclass/序列，mapping/set保留旧repr排序与局部物化。内容字节/hash差分与合成内存分配测试26项通过；与旧normal相关回归108 passed in14.98s。它尚未接入任何执行路径，合成编码峰值改善不等于真实H25资源通过。旧normal源码将自身hash纳入依赖，因此后继接入必须显式绑定新实现并保留旧声明/结果，不能静默更新原pins。

下一必要工作为受限真实来源下验证新编码的身份等价性和内存表现，再设计明确绑定实现的接入；来源准备、normal/replay/current/四臂真实规模与恢复/右删失、科学注册和正式启动门继续开放。


流式原语最终补记：独立相关回归108 passed in14.70s，限定pre-seal无开放实质finding；source/test hashes及命令见docs/model_spec/rq2_identity_stream_v1.md。独立核验确认原22项及新probe13项bytes/hash均匹配。后继先清点source assembly/validate、pair binding、normal execution/store/replay全部身份调用点，设计显式绑定新原语与adapter bytes的后继合同，再开展真实H25身份/资源验证；不把局部替换当作完整接入，不复用旧execution pin宣称新实现已执行。


## 2026-09-21 流式来源组装后继与全链清点

已新增独立 source_normal_stream.py（DRAFT_NONAUTHORITATIVE），在外部 implementation pin 下复用来源校验/loader及原输入验证，流式计算完整年度输入摘要；新类型分别保留 normal 内容、旧 assembly 内容对照、新实现和新 assembly 身份。旧代码、旧执行 pins、失败 attempt 和 probe 保持，不能用新候选冒充旧执行记录。接入清单已覆盖 prepare、pair/power binding、kernel build、execution/store/replay，以及 common_request_adapter/grid_information/outage_trajectory，详见 docs/model_spec/rq2_source_normal_stream_v1.md。

主相关回归165 passed in17.91s，含33项新适配器测试；原 attempt 的22项、probe的13项文件bytes/hash核验一致。独立审查提出的loader原对象冗余引用已在hash前释放，并用weakref测试验证。本次仅完成来源候选层，尚未接入整任务，未执行真实H25或solver。下一必要工作是独立受限零solver H25来源组装的内容对照与资源验证，再依清单接通后继链；完整prepare/normal/current/四臂资源、恢复右删失、科学注册及正式启动门继续开放。


## 2026-09-21 真实 H25 流式来源组装验证完成

独立流式来源候选已取得真实数据证据：probe2保留完整8784小时RTS数据，25小时请求对应raw0..24/source1..25；normal内容摘要d9959966…与旧assembly内容reference626f7dbe…均复现，新assembly身份689ac1bc…独立记录。source阶段8.862秒，进程10.89秒exit0、Job静默true，51次采样；process/Job commit峰值339828736/341061632 bytes，低于原768 MiB cap，working-set峰值362663936 bytes，无reserve/API error，solver_calls=0。机制初值与workload-power映射标签保持，不转为真实观测。

先前probe1在来源开始前exit1；只读复算定位到环境dict插入序导致父子进程身份不同。保留v1/probe1全部字节，v2只修复环境指纹重建并验证实际键值，独立55项通过。完整证据与边界见docs/model_spec/rq2_source_normal_stream_v1.md；probe2 root为results/tables/rq2_stream_source_probe2_non_authoritative，13工件hash索引为results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/stream_source_probe2_evidence.json。

下一必要工作已从“验证来源流式编码”推进到后继power/pair binding与prepare整链接入，须保留独立实现pins并核验重复重建/快照的资源。此次只证明一次来源候选内容复现与受限进程观察，未证明完整prepare、normal执行/replay、current/四臂资源、完整恢复或右删失口径；科学注册与正式启动门继续开放。原22+13+11项历史工件及新13项bytes/hash均核验一致，未清理仓库。


## 2026-09-21 流式 binding 与 prepare 整链接入完成（开发态）

已新增pair_normal_stream.py与normal_task_inputs_stream.py，贯通pinned机制声明→流式来源组装→来源重建→power窗口对应→pair业务baseline→完整prepare。来源重建的owned快照供power和baseline共用，省去额外年度assembly deepcopy；旧内容报告canonical JSON与原saved binding逐字节核验，新source/binding/prepare指纹独立绑定。旧full-input hash/binder不在新prepare路径中，旧执行链未被修改。

相关回归140 passed,1 deselected in19.52s；独立binder+prepare targeted45 passed in14.71s，限定pre-seal无开放实质finding。排除项为旧uncontained真实H25准备测试，未用tiny结果声称真实资源通过。规格、命令、hash与边界见docs/model_spec/rq2_normal_task_inputs_stream_v1.md。原22+13+11+13项工件bytes/hash保持。

下一必要工作为同768 MiB开发预算下的一次受限零solver真实H25完整prepare验证，重点观察caller assembly与rebuilt同时存在的峰值，再接normal execution/store/replay及current/四臂。科学参数仍按机制假设标注；来源/prepare开发进展不关闭恢复右删失、风险分母、科学注册或正式启动门。


## 2026-09-21 真实 H25 完整流式 prepare 验证完成

受限零solver探针已终态成功：prepared_content_reproduced，errors=[]，完整8784小时数据保留，旧normal/assembly/binding内容全部复现，并单独记录新prepare/binding identities。prepare本体31.440253秒，进程33.734秒exit0、Job静默true，156次采样；process/Job commit峰值474931200/476151808 bytes，working-set峰值496750592 bytes，无reserve/API error。原768 MiB上限保持；initial state/workload-power等机制假设仍未变成真实观测。

probe主相关114项、独立69项通过后运行一次；15项证据索引为results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/stream_prepare_probe1_evidence.json，详细命令、hash和分段耗时见docs/model_spec/rq2_normal_task_inputs_stream_v1.md。历史22+13+11+13项与本次15项bytes/hash均匹配，旧失败记录/源码全部保留。

下一必要工作推进到normal模型build/audit与数值执行的流式后继，覆盖内部旧normal identity调用，随后连接store/replay/controller与current/四臂。此次只验证完整输入准备，未求解normal或验证assignment，whole_task_resources_verified/formal_result均false；恢复右删失、风险分母、科学注册及正式启动门继续开放。

## 2026-09-21 流式 normal 模型与同步内核开发

新增 continuous_grid_normal_stream.py 与 normal_execution_stream.py，保持旧模型和数值门，另绑新实现及执行身份。合成 H1/H25/H49 的完整变量、约束线性系数与目标逐项对比一致，assignment 故障与原生求解失败语义验证通过；旧执行 pin 不能授权新内核。两项新模块及旧模型/旧内核/identity_stream 相关回归共242 passed in63.40s。详见 docs/model_spec/rq2_normal_execution_stream_v1.md。

本轮仍为 DRAFT_NONAUTHORITATIVE，真实来源证据止于完整prepare；新内核尚未接入来源执行/store/replay/controller，未证明真实 H25 assignment 或整任务资源。下一必要工作为消费独立新 source/prepare/binding pins 的来源执行后继，随后完成持久化和独立回放。历史五批74项工件bytes/hash保持一致。科学注册、恢复右删失及正式启动门保持开放。

独立只读 R3 pre-seal 审查：两新文件80 passed in32.28s，未发现需返工的实质finding；同步检查不能替代Job硬资源限制，外层来源绑定与整任务资源仍待验证。此次无official verdict/receipt。


## 2026-09-21 流式来源执行与声明入口开发

新增 source_normal_execution_stream.py 和 normal_declared_execution_stream.py，接通外部 pinned request→完整流式prepare→source/pair重建与binding→normal kernel→返回后声明及实现链复核。tiny三小时合成网络经过实际HiGHS求解，objective=120、terminal carry.source_hour=3；公开loader/package仍为synthetic fixture，不能视为真实RTS规模或业务观测。

新入口要求独立的新source/binder/assembly/binding/request/kernel/source execution pins，旧内容reference不授权新执行。post-source或post-declaration失败保留已返回数值证据及调用数，缺完整owned返回保持unknown，无自动重试。详见 docs/model_spec/rq2_source_normal_execution_stream_v1.md。

下一必要工作为把声明入口接入已有一次性intent/result日志的流式后继，并实现嵌套证据独立replay，再接controller/worker Job监督。真实H25证据仍止于prepare，whole-chain资源、current/四臂、恢复右删失、风险分母、科学注册和正式启动门继续开放。旧五批74项诊断工件bytes/hash一致。

最终相关回归201 passed,1 deselected in155.96s，排除旧未受Job监督的真实H25测试；独立只读R3 pre-seal审查无开放实质finding。详细测试与工件SHA见上述规格，未生成official verdict/receipt或正式运行授权。


## 2026-09-21 流式声明一次性日志开发

新增 normal_declared_store_stream.py，接入完整声明执行入口。日志只持有小型pinned request，在独立intent COMMIT及readback后才运行prepare/source/kernel，保存完整DeclaredStreamingNormalResult嵌套证据。沿用NTFS lease和SQLite事务合同，新schema/application ID与旧日志分离。首轮19项通过，覆盖四个真实进程退出窗口；新增声明漂移、wrong返回、intent早于prepare和完整wire核验，详见 docs/model_spec/rq2_normal_declared_store_stream_v1.md。

当前日志只提供一次性调用与内容完整性，numerical_evidence_replayed/native_execution_authenticated/formal_result仍false。下一必要工作是独立重建并回放三层nested result的流式replay，再接worker/controller Job监督与真实H25资源验证。旧五批74项诊断工件bytes/hash一致；current/四臂、恢复右删失、风险分母、科学注册和正式启动门继续开放。

主相关回归81 passed in202.15s，独立新日志26 passed in100.65s；限定R3 pre-seal审查无开放实质finding。源码、测试hash及完整命令见日志规格，未生成official verdict/receipt或正式运行授权。


## 2026-09-21 流式声明日志独立回放开发

新增 normal_declared_replay_stream.py，从独立pinned request重建prepare/source/binding，解析声明→source→kernel三层wire，零solver复核原生数值、完整assignment/witness、调用记账和timing/peak/payload。store入口要求独立current head，genesis不授权数值回放。新增拒绝词表与静态错误投影、prepare role消费门，修复伪造降级拒绝可被误判一致的pre-seal finding。详见 docs/model_spec/rq2_normal_declared_replay_stream_v1.md。

结果仍区分archive consistency与原生/测量认证，native_execution_authenticated/resource_measurements_authenticated/resume_authorized/formal_result均false；历史动态异常只能核记录相容性，不认证其实际发生。下一必要工作是接入固定worker、归档捕获及controller的流式schema后继，在Job内覆盖执行与独立replay，再验证真实H25全链资源。旧五批74项工件bytes/hash一致，current/四臂、恢复右删失、风险分母、科学注册和正式启动门继续开放。

验证：78项全组通过后，末次phase审查补2项反例明确复现失败，修复后受影响16项通过；旧normal/native回放相关104项通过。各批范围、命令和最终源码/测试SHA见回放规格，不把前一候选的通过结果冒充最后修复的直接证据。

末次独立只读R3 pre-seal受影响6项通过，最终SHA一致，两轮findings闭合；未生成official verdict/receipt或打开正式门。


## 2026-09-21 流式声明归档有界捕获开发

新增 normal_archive_capture_stream.py，复用原budget和64 KiB只读分块捕获，连接新声明日志schema/application ID与declared execution pin。result claim仍opaque，必须经独立replay核验。补齐unused时header执行pin交叉核验，新增反例先复现失败再修复；双向旧新schema隔离、禁止prepare/model/solver和完整capture→replay链已有tiny测试。

相关回归91项通过后完成上述修复，最终新capture全组36项通过；旧五批74项工件bytes/hash一致。详细命令/范围/SHA见 docs/model_spec/rq2_normal_archive_capture_stream_v1.md。下一必要工作为固定worker及controller接入，必须保留prepare后求解前的packet/cwd/environment/argv与身份复核位置；当前尚未实现这一连接。真实H25全链、Job资源、current/四臂、恢复右删失、风险分母、科学注册和正式启动门继续开放。

独立只读R3 pre-seal全组36项通过，最终SHA一致，finding闭合；未生成official verdict/receipt或运行授权。

## 2026-09-21 流式固定 worker 与求解前运行态复核

新增 normal_task_worker_stream.py，把独立 compact pins、一次性声明日志和独立 replay 接入固定 execute/replay 分支。声明入口和日志的未seal draft 增加 before_source 检查位置；固定worker在 intent COMMIT/readback→prepare 后、source求解前核对 packet/cwd/environment/argv/intent/launch/claim及身份。检查失败保持 unresolved intent，不求解、不重试。旧worker/controller及冻结输入和结果不变。详见 docs/model_spec/rq2_normal_task_worker_stream_v1.md。

相关回归118项通过，另6项因新增测试漏传重开日志 required expected_head 而失败；修复测试后6项重跑通过。独立replay相关8项通过。完整命令、分批范围与当前SHA见规格，不把此记录写成最终124项整组通过。五批74项历史工件bytes/hash一致。

下一必要工作是流式controller后继：消费新的declared/source/native嵌套报告，保留两Job顺序、静默后独立双capture及完整资源门。真实H25观测仍止于完整prepare，尚无新全链assignment或整任务资源证明；current/四臂、恢复右删失、风险分母、科学注册与正式启动门保持开放。

独立只读R3 pre-seal审查最终worker全组29 passed in125.44s，journal callback定向2 passed,26 deselected in6.39s；最终源码/测试SHA一致，无开放实质finding。该结论不认证Job membership、整Job静默或资源上限；controller接入和真实H25全链仍待完成。未生成official verdict/receipt或运行授权。

## 2026-09-21 流式controller与真实H25全链开发观测

新增 normal_task_controller_stream.py，完成declared/source/native三层报告核验、顺序两Job、静默后独立双capture和完整报告复读。pre-seal发现未知/重复错误及遗漏native错误投影的降级报告漏洞，四项反例先复现失败再修复；最终报告23项、controller与runner68项、相关134项通过；独立报告/双Job24项及runner7项通过，finding闭合。详见 docs/model_spec/rq2_normal_task_controller_stream_v1.md。

随后新目录真实H25单次短开发验证完成：总274.39秒，execute151.094/replay119.812秒，均exit0且整Job静默，Job commit峰623742976/624693248 bytes，低于原805306368上限。capture前后pins一致，replay archive_consistent=true/errors为空，但数值仍unresolved：native calls=1、solution_count=0、aborted/maxTimeLimit；normal总耗时67.5576574秒超过60秒门。没有有效assignment或terminal witness，不能推断数学不可行，也不报告全四臂/恢复/工程认证。初态和业务功率映射仍为机制参数。

旧五批74项工件保持；新增结果索引 stream_task_attempt1_evidence.json 绑定54项，SHA4f5c61bc8f4ebfa615448cfbbb29c45ae25409e8d290c8583847ae9aff001f1c。原始观测、预算和解释见 docs/model_spec/rq2_normal_task_stream_h25_development_v1.md。相关代码与声明现被真实工件绑定，后续使用明确后继，不覆写本次记录。

下一必要工作：定位normal preflight/pipeline和末端检查的时间开销，保持全部身份/数值/资源门；随后取得有效normal assignment，再接current/episode。whole_task_resources_verified仍false；完整UID/four-arm、恢复右删失、风险分母、科学注册及正式启动门继续开放。


## 2026-09-27 真实H25零求解组件成本定位

normal组件探针已完成：最终相关193项通过，独立审查发现并闭合父进程汇总前后实现漂移窗口，两项反例先失败后通过。一次真实H25测量保留完整8784小时来源和原768 MiB上限，正常退出且Job静默，86.125秒，Job commit峰476012544 bytes，solver_calls=0，model_builds=1；normal/assembly/binding内容复现。详见 docs/model_spec/rq2_normal_component_cost_probe_v1.md。

完整input identity两次分别10.223881/9.739884秒，model build10.610566秒（含内部校验），完整prepare47.835529秒。下一必要工作为保留逐字节编码与全部检查位置的身份编码性能后继；本次测量未细分验证/递归编码/SHA成本，不能直接外推旧67.56秒或声称60秒门已过。尚无有效normal assignment，随后仍须完成current/episode与完整UID/four-arm资源验证。

29项证据索引 normal_cost_probe1_evidence.json 位于 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative，SHA7f0d5fa4fb3fce23588bbb117bfa319ca3abdb1f987e609ff6a240ac924a9e50。六批历史128项索引绑定、公开数据交付包7文件、复合诊断7文件与16依赖核验一致；连续多日、恢复债务、四臂、拒绝动作与诊断已有产物继续复用。机制初态与功率映射仍非真实业务观测；恢复右删失、风险分母、科学注册及正式启动门继续开放。


## 2026-09-27 身份编码后继的真实等价与性能对照

新增identity_stream_fast.py，保持原JSON字节、float hex与repr排序，完整重算验证/依赖，不缓存输入或摘要。相关新旧identity/cost回归157项通过，独立identity41项通过。新增受限对照probe相关170项及独立差分14项通过；旧实现和既有工件全部保留。

真实H25一次零solver对照已完成：四次old/fast内容摘要一致；旧identity9.834936/9.786799秒，新6.865299/6.754984秒，本次耗时减少30.19%/30.98%。Job98.625秒、exit0且静默，commit峰475328512 bytes，仍在原768 MiB上限内。数值模型仍使用旧kernel，未验证新kernel或60秒门，也未产生assignment。

详见 docs/model_spec/rq2_identity_stream_fast_v1.md；31项索引为 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/normal_identity_comparison_probe1_evidence.json，SHA08eee9f3134b3f82e6eb59a3c5fd920fb087e99178b3b16979a1f08d0166d316。下一必要工作为接入独立normal模型/内核后继，保留全部身份复核和数值/资源门，再验证完整执行链。有效normal解、current/episode、完整UID/四臂资源、恢复右删失、风险分母、科学注册及正式启动门仍开放；机制初态与业务功率映射仍非真实观测。


## 2026-09-27 快速编码接入normal模型、内核与声明入口

新增continuous_grid_normal_stream_fast、normal_execution_stream_fast、source_normal_execution_stream_fast和normal_declared_execution_stream_fast四个独立后继。新CONTRACT、owned result类型与execution pins区分实现；保留模型全矩阵、全部身份复核位置、数值/资源门、source前后绑定与求解前callback。来源prepare/binder继续复用现有stream路径。旧源码、配置和八批188项历史工件bytes/SHA保持。

新旧模型/kernel相关204项、来源/声明/prepare/binder相关115项通过；随后新增callback失败窗口四项，定向9项通过，未声称最终119项单次整组通过。独立模型/kernel31项、来源/声明4项及新增callback4项通过，pre-seal测试覆盖缺口闭合。tiny完整声明链得到objective120、terminal source_hour3，仅为显式合成来源；详见 docs/model_spec/rq2_normal_execution_stream_fast_v1.md。

下一必要工作为新类型的持久化日志和独立replay后继，随后连接固定worker/controller并做真实H25受限验证。尚未运行真实fast kernel，不把此前编码30%改善外推为60秒门通过或有效normal assignment；current/episode、完整UID/四臂资源、恢复右删失、风险分母、科学注册和正式启动门继续开放。机制初态与业务功率映射仍非真实观测。


## 2026-09-27 fast日志、回放、归档与固定worker接入

新增normal_declared_store_stream_fast、normal_declared_replay_stream_fast、normal_archive_capture_stream_fast与normal_task_worker_stream_fast独立后继。新schema/application ID/owned types与旧链隔离，intent先于prepare、完整三层数值回放、current head要求、opaque有界capture和prepare后source前运行态复核保持。旧文件与八批188项工件bytes/SHA一致。

日志/回放首轮108项及后加隔离定向6项通过；capture首轮37通过1项测试fixture失败，修正多余fixture依赖后最终全38项通过；worker首轮29项及后加旧request type定向1项通过。分批计数不混写为最终一次全组结果。独立日志/回放7项、四个真实进程窗口4项、capture4项、worker关键链8项及旧type1项通过；限定pre-seal审查无开放实质finding。详见 docs/model_spec/rq2_normal_persistence_stream_fast_v1.md，含命令、准确时间及最终hash。

下一必要工作为fast controller消费新worker/request、capture和三层replay报告，保留两Job顺序、整Job静默后双capture与原资源门，再做真实H25受限开发验证。当前仍只有tiny正例和真实固定argv缺失来源负例，未运行真实fast kernel或取得有效normal解；不能从编码改善推断60秒门通过。current/episode、完整UID/四臂资源、恢复右删失、风险分母、科学注册及正式启动门继续开放，机制参数继续与真实观测区分。


## 2026-09-27 fast controller 与真实 H25 单次验证终态

fast controller/runner 已接通新 worker、双 capture 和三层 replay；最终相关回归 92 passed in 223.37s，独立 pre-seal 定向 9 项及 34 项通过。一次受限 H25 开发任务已结束，execute/replay 均 exit 0 且 Job 静默，归档和来源回放一致。normal 63.5284186 秒超过原 60 秒；1 秒 solver 调用返回 aborted/maxTimeLimit、solution_count=0，无 assignment/witness，仍为 unresolved，不能解释为数学不可行。

API 返回 completed_development_replay_diagnostic，落盘 observation 为 validated_before_final_observation_write，分别保留。新 76 项证据索引 stream_fast_task_attempt1_evidence.json 的 SHA256 为 91dda12ffceb2463b3fa1fda666ede79d23d0b888953a223e3e3eb1d1ca94a69，位于 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative；旧八批 188 项 bytes/SHA 重核一致。详情见 docs/model_spec/rq2_normal_task_stream_fast_h25_development_v1.md。整任务资源、native authentication、formal/security 门均未解除；机制初态与业务功率映射不是真实观测。

下一必要工作改为进一步定位 normal 身份复核/构建/加载耗时，并独立诊断 1 秒求解无可行解；保留原限额和复核点，在明确后继中开发。本次绑定代码/配置/结果保留，已有连续多日、债务、拒绝动作、四臂及回放组件不重复开发。有效 normal、真实 current/episode、完整 UID/四臂资源、恢复右删失、风险分母、科学注册及正式启动门继续开放。


## 2026-09-27 身份分段定位与数值映射编码对照

真实 H25 零 solver 分段测量已完成：validation 0.0039583 秒、dependencies 0.0165303 秒、encoding+digest 4.7174440 秒，优先优化编码有实际依据。新分段工具 100 项、相关旧工具/fast 编码 136 项通过，独立窄测 8 项及 33 项结果索引审计闭合。详情见 docs/model_spec/rq2_normal_identity_breakdown_probe_v1.md。

新增 identity_stream_numeric 仅特化 exact primitive-key/float-value 字典，保留完整 repr 排序、finite/float.hex、旧类型回退与所有 validation/dependency 复核，无缓存。新旧编码相关 118 项通过，独立新 51 项及 2000 个随机映射字节/摘要对照一致。真实对照 probe 首轮多余参数错误已修复，最终 156 项及独立 4+28 项通过。

一次真实零 solver 对照取得 fast 5.4537921/5.1988746 秒、numeric 4.3547956/4.2227902 秒，单次局部观测下降约 20.15%/18.77%，所有输入摘要与模型结构保持。Job 88.078 秒、exit 0 且静默，commit 峰 474370048 bytes；仍使用 fast 模型，尚未验证 numeric kernel 或 60 秒门。37 项索引 normal_numeric_identity_probe1_evidence.json 的 SHA 为 7ce289bed9a74d99e1e39fc495f8f8813e06443e6ff5f0eb25a7349b57ec4dfe，位于 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative。详见 docs/model_spec/rq2_identity_stream_numeric_v1.md。

下一必要工作为 numeric 编码的独立 normal 模型/kernel 后继及完整链验证；1 秒求解无可行解仍单独 unresolved。机制初态与业务映射仍非真实观测，有效 normal、current/episode、完整 UID/四臂资源、恢复右删失、风险分母、科学注册和正式启动门继续开放。既有多日/债务/拒绝动作/四臂产物及全部历史协议、代码、结果保留。


## 2026-09-27 numeric 完整执行链与 H25 开发终态

numeric normal 模型/kernel/source/declared、持久化/独立回放/capture/worker/controller/runner 后继均已接通。完整矩阵、所有身份复核点、旧机制与资源/数值门保持；numeric fallback 依赖显式绑定。root 分组终态为179、121、118、71、61、33 passed，独立 pre-seal finding 闭合；不是单次全组统计，也不构成 official review 或正式授权。

一次 numeric H25 开发任务已完整结束，normal 53.8714377 秒，本次未触发原60秒超时；native仍为1 call、aborted/maxTimeLimit、solution_count=0，无assignment/witness，数值状态保持 unresolved。execute/replay147.25/121.656秒，均exit0且Job静默；双capture和零solver replay一致。不同运行时点的53.87与旧63.53秒不可用来证明受控性能提升或一般资源保证。

新99项索引 stream_numeric_task_attempt1_evidence.json，SHA d5679002d9c4a388a4c955eb4a95096321169196eb26bf3c1a266d46180ad983，位于 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative；自包含11个历史索引映射，旧334条bytes/SHA保持。详细测试、命令、预算、记录和解释见 docs/model_spec/rq2_normal_task_stream_numeric_h25_development_v1.md 及其引用的三个实现规格。

下一必要工作转为独立有界的native求解阶段诊断，区分model transfer、presolve和搜索；现有证据不能定位1秒无solution的内部原因，不能据此放宽门槛或宣称不可行。有效normal、真实current/episode、完整UID/四臂资源、恢复右删失、风险分母、科学注册与正式启动门继续开放；机制初态和业务功率映射仍非真实观测。所有现有未提交文件、旧协议和结果保留。


## 2026-09-27 native 求解阶段诊断

单次有界 H25 开发诊断已完成：set_instance 1.7605765秒、optimize 1.0094633秒、legacy interface 2.7725891秒；1 call，aborted/maxTimeLimit、noSolution，simplex_iteration_count=4844、mip_node_count=0。进程exit0且Job静默，60.969秒、commit峰526721024 bytes。计数器不能证明不可行，presolve/搜索细分仍未知；接口耗时不能与旧完整normal pipeline直接作性能差值。

helper/runner独立pre-seal已闭合；helper独立36项通过，补齐最终runner依赖pin后runner85项包含于215项相关回归终态。新38项证据索引 normal_solver_phases_probe1_evidence.json（SHA256 5ed4385cf074e0dc5e260a7ba11ab3c3d7ea1c6f0fd70449b303e46939f6ad89），位于 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative；另复核12个历史索引的433条证据一致。完整规格、预算、测试时序和结果解释见 docs/model_spec/rq2_normal_solver_phases_probe_v1.md。

当前仍缺满足原最优性和witness验收的有效normal。下一项是预先固定后继有界可行性验证的预算、成功标准及失败语义，保留原1秒探针与全部旧结果；不把到时无解当不可行，也不以incumbent代替原验收。真实current/episode、完整UID/四臂资源及正式实验门继续开放，机制初态和业务映射仍非真实观测。

本次独立只读结果审计已闭合，38项新证据与433项历史证据、进程/来源/身份/计时链均复算一致，无开放实质finding；不构成official verdict或正式实验门证据。


## 2026-09-27 五秒完整 normal 开发终态

固定5秒、1 thread的numeric完整任务已执行一次，无重试。normal51.3511618秒、errors=()，native仍为1 call、aborted/maxTimeLimit、solution_count=0，无assignment/witness。60秒normal及全部数值门保持，未解不能判不可行。execute/replay131.438/103.297秒，均exit0且Job静默，独立回放archive/source一致、errors=[]、solver calls=0；accepted_record_reproduced=false。API completed_development_replay_diagnostic与落盘validated_before_final_observation_write对应不同写入时点。

新20项与旧runner8项共28 passed（5.29秒），独立20项通过。新98项索引 numeric_5s_task_attempt1_evidence.json（SHA256 4dc646b77c9e5aa71114b577117fc6a6493976c6e0a0fc6f7d9bcdb2cca55af6），位于 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative；另13个历史索引/471条旧证据复核一致。详见 docs/model_spec/rq2_normal_task_numeric_5s_h25_development_v1.md。

下一步核对当前Gurobi接口与相同模型的有界交叉验证路径，复用已有adapter和旧跨引擎证据，不继续机械增加HiGHS时间。旧pilot不直接认证当前H25，正式引擎选择与正式运行门保持关闭；原机制初态、业务映射与未解状态不变。


五秒结果独立只读审计已闭合，98/98新项、13个历史索引/471条旧证据及结果解释一致。随后tiny检查定位当前Pyomo默认Gurobi接口的solution status字符串与现有严格枚举门不兼容；新增独立direct接口draft，在pytest内注入后通过原native/完整assignment/normal witness逻辑，补齐类型定义源码绑定后15项测试通过。该factory尚未集成到独立身份的H25执行与回放链，不能作为有效H25 normal或正式引擎选择证据。详见 docs/model_spec/rq2_gurobi_direct_development_v1.md；下一项为该接口的最小normal后继集成。


## 2026-09-27 Gurobi direct 完整链与许可证阻塞

Gurobi direct 的 normal/source/declared/store/replay/capture/worker/controller 后继已接通。最终分组检查为核心156、store/replay118、worker/controller/reports117、runner20项通过；capture40项在此前分组通过，独立pre-seal实质finding已闭合。共享数学模型、机制输入、容差和资源门保持，已有连续多日、恢复债务、四臂及拒绝动作实现无需重建。

固定5秒、1线程H25开发任务已执行一次：normal42.8698899秒，native调用因 `Model too large for size-limited license` 失败，并保留 `structure_options_or_version_drift`；没有assignment/witness或可行/最优证据。execute/replay122.797/102.828秒，均exit0且Job静默；零solver回放确认archive/source一致，accepted_record_reproduced=false。该失败属于运行环境/许可容量阻塞，不能解释为数学不可行或Gurobi求解性能不足。

宿主存在GRB_LICENSE_FILE指定的许可文件；当前受控environment未传入该键，继承的exact whitelist亦不允许该键。下一必要工作是显式许可证路径传递的最小后继及同受控环境容量核查；许可文件内容不进入仓库，不修改本次已绑定源码/配置/结果。现有tiny测试不足以证明许可容量。真实current/episode、完整UID/四臂资源、恢复右删失、风险分母及正式实验门继续开放；业务映射与初态仍是机制假设。

本次122项证据索引为 results/tables/rq2_normal_task_h25_audit_v1_non_authoritative/gurobi_direct_task_attempt1_evidence.json，SHA256 289173afc81967b76eeb7cbc58ed8588fd695d5313f9eda2234ecfc79d9c0da0；另14个历史索引/569条旧证据经root复核一致。详细范围和实测见 docs/model_spec/rq2_normal_gurobi_direct_chain_v1.md。

独立只读结果审计已核对122项新证据及569项历史证据一致。许可变量未传入受控child已确认；calls=1是wrapper调用前计数，不证明进入optimize。structure_options_or_version_drift是异常路径中pre_structure=None触发的次生guard标签，不是独立观测到漂移。该结果保留为环境失败，不开启正式门。

## 2026-09-27 许可修复与首份H25完整可行赋值

显式许可环境后继已完成，同受控环境22275变量/28004约束合成容量检查通过。复用既有normal内层，仅后继环境codec、worker/controller及声明runner；125项外层、20项runner、2项身份反例通过，独立pre-seal闭合。固定5秒H25首次得到完整可行赋值；零solver回放确认assignment/witness、来源及残差一致。许可阻塞在该环境已排除。

有效normal门仍开放：原生到时终止、optimal=false，所报界相对gap约0.267%；完整normal71.429665秒，超过原60秒门。下一工作针对完整赋值路径的校验开销及有界最优性，保留全部数值/资源标准，随后才推进真实current/episode。机制初态和功率映射仍非真实观测；四臂资源、恢复右删失、风险分母与正式注册/运行门不变。

详细证据见docs/model_spec/rq2_normal_gurobi_licensed_v1.md；新138项索引gurobi_licensed_task_attempt1_evidence.json位于results/tables/rq2_normal_task_h25_audit_v1_non_authoritative，SHA256 fd6d0f32a768866282b4dd2b1211c817956d4ede16daa5ca9f53847abdfdd9b2；另15个历史索引/691条证据已复核一致。

独立只读结果审计已闭合：138项新工件、691条历史证据以及赋值/witness/回放、双capture、计时与验收字段一致，无开放实质finding；不构成official verdict或正式门授权。

## 2026-09-27 结构身份等价比较

新增单次调用内变量名复用与primitive优先编码helper，保留原完整结构字段/排序/数值规则。87项组合及3项新增依赖漂移反例通过；独立pre-seal闭合。一次零solver H25构模ABBA比较的四次结构摘要与旧e18f值一致：旧1.79–1.83秒/次，新1.29–1.43秒/次。Job47.891秒、exit0且静默；只证明局部等价及本次耗时，不能外推完整normal的60秒门。

暂不为此局部收益机械后继整条执行链；下一项复用既有numeric输入身份约4.22–4.35秒/次的观测，优先降低完整编码成本并保留全部检查位置/字节。有效normal最优性、60秒及后续正式门仍开放。详见docs/model_spec/rq2_grid_structure_fast_v1.md；新118项索引grid_structure_fast_probe1_evidence.json（SHA256 fb1291f309030428ee9377c25d8593969188e55f31e51945faf33edcb574287b），另16个历史索引/829条旧证据一致。

## 2026-09-28 完整输入编码比较与执行集成

完整年度输入ABBA比较已完成，numeric约3.93秒/次、ordered约2.12秒/次，四次输入摘要一致；零构模、零solver。122项新证据及947条历史证据的独立结果审计闭合，详见docs/model_spec/rq2_identity_stream_ordered_v1.md。此局部改善支持接入完整链验证，不能直接推出60秒通过。

当前必要工作为gurobi_ordered完整执行集成：保留全部检查、源数据与机制参数、60秒/768MiB门，预先固定单次15秒求解预算；runner20项测试通过，内外层回归及独立pre-seal进行中，尚未启动新H25任务。详见docs/model_spec/rq2_normal_gurobi_ordered_v1.md。有效normal、真实current/episode及四臂完整资源、恢复尾部与正式协议门均未据此关闭。

完整集成验证及独立pre-seal现已收束，单次H25运行与零solver回放完成：normal56.4923187秒，在原60秒门内，完整赋值/witness及回放一致且errors=[]；15秒求解到时，optimal=false，gap约0.125%，normal_accepted=false。当前normal阻塞已集中到最优性，下一步针对有界求解收敛，不再新增独立编码探针；本次normal余量约3.51秒，不能直接延长求解并假定总门可过。详细状态、界和资源见docs/model_spec/rq2_normal_gurobi_ordered_v1.md。169项新证据索引gurobi_ordered_task_attempt1_evidence.json，SHA256 1aeebb6f2ea6b1416f689f232c95d2fc9b7473265f8233b0754f43b6a1810da3；18个历史索引1069条证据保持。正式门及其他科学输入缺口继续开放。

同配置单次15秒convergence诊断已完成：根松弛约0.5秒，约2秒进入搜索，终态730节点、原生SolCount=9，仍TIME_LIMIT，日志gap约0.1263%。这定位到已进入分支搜索后的有界收敛问题；尚不能归因某一具体启发式。下一项验证声明的线程并行度，保留模型与数值/资源门，不据此选择正式引擎。156项新索引gurobi_convergence_probe1_evidence.json（SHA256 008be53a6cf7593c27b5ac6903026103eeef96d45ade190d5a7aeca81d2b795d），19个历史索引1238条证据一致。细节及诊断/完整执行的计时区别见docs/model_spec/rq2_gurobi_convergence_profile_v1.md。

Threads参数=4的单次15秒诊断现已完成：仍TIME_LIMIT，原生1721节点/SolCount10，日志gap0.203%；Job62.656秒、commit峰752758784 bytes，在768MiB内。child60.0569秒属于prepare+diagnostic，不能与normal60秒门混用。参数回读不认证实际worker利用率，顺序单次结果不支持因果性能比较。该attempt未收敛，不接入完整normal链；下一步核查可行赋值warm start的输入/结构同一性、审计及累计成本前提，不重复已有连续transition/reserve envelope，也不添加会删除crossing trajectories的逐时排序。160项新索引gurobi_four_thread_probe1_evidence.json（SHA256 30bf1e3de7bea997d7418b0efd343a447a9d7f9c2b493f2f5c95b5fddc96a175），20历史索引1394条证据一致。详见docs/model_spec/rq2_gurobi_four_thread_profile_v1.md；正式门保持。

## 2026-09-28 warm start前提与资源门来源核查

零solver读取既有H25 SQLite：完整性正常，6806997-byte record的SHA256仍为2fc450ac5e19e434dcb8e2f7408b9beb442e89113e732f1d3cec63967d54173e；loaded_values为22275个唯一、有限值，与initial_values有序变量名一致。可作为候选start，不证明新调用收敛。复用来源链已有一次solver调用，必须区分新调用计数与累计来源成本；不能把离线求解结果视为免费外生观测。

进一步核实normal的30秒solver/60秒wall上限来自短开发内核，normal_accepted也不等于formal-ready。旧ordered声明及结果保留原60秒门；这一开发cap不自动成为所有正式任务的科学验收标准。现有EpisodeBudget仍最多120次/60秒solver预留，而H25全158 UID路径需要19900次加normal一次，说明完整资源合同依然是独立缺口。

当前动作调整为先形成真实规模资源方案及验收矩阵，明确normal、current/selector、全episode与预计算成本；暂不新增warm-start整条执行链或H25探针。保持gap、残差、物理约束、来源、右删失及四臂公平性，未改变任何旧预算或启动更长运行。细节见docs/model_spec/rq2_normal_warm_start_feasibility_v1.md。
## 2026-09-28 显式任务清单核算实现

新增execution_workload.py和规格docs/model_spec/rq2_execution_workload_v1.md。由显式normal/episode清单核算完整UID reference及四臂actual调用和各自solver预留；共享normal仅按明确依赖计一次，每个容量评估仍独立列项。拒绝重复ID、缺失依赖、split/输入/UID不一致和非连续或越界小时，不默认将46 cells视为完整任务数。报告回显完整声明，固定保留来源/复用、清单完整性、wall/内存/磁盘和正式注册未解项；不提供执行准入。

26项零solver针对性测试通过（1.53秒），与现有EpisodeSession._requirements及独立逐阶段枚举一致。只读核对既有source record的158 UID/25行，示例预算normal15秒、selector每阶段1秒得到19901 calls/19915秒solver预留；这不是建议预算或真实运行。进一步确认reference/actual入口只接受max_calls<=20的GridDevelopmentBudget，无法容纳160/159级，不能只提高episode cap后运行。下一项补独立真实规模selector/episode资源合同，保留完整阶段与原数值审计；旧执行类型、配置和结果未改。
## 2026-09-28 完整串行资源声明合同

新增execution_resource_contract.py和docs/model_spec/rq2_execution_resource_contract_v1.md，在显式workload清单上要求每个normal/episode都有完整wall、非solver开销、Job commit、archive/scratch、线程及模型规模上限。检查单任务预留、总wall、最大串行Job加supervisor/reserve，以及不回收scratch的全量磁盘需求。预算短缺逐项报告，完整声明可重建；declaration_consistent不表示资源实测或运行准入，三个资源验证/授权/formal标志固定false。

组合42项零solver测试通过（主代理1.59秒、独立复跑1.58秒），代码限定审查无实质finding。旧budget类型、selector、episode及结果未改。真实规模入口接入、实际模型/宿主/多卷空间核验、硬进程监督和normal最优性仍缺；下一项为保留全部UID阶段与数值审计的独立selector执行接口，先以合成例验证，不启动依赖accepted normal的真实episode。
## 2026-09-28 完整UID selector接口与合成验证

新增scale_selector.py和docs/model_spec/rq2_scale_selector_v1.md。独立预算由完整资源合同派生，保留原reference request→L1→全部UID和actual L1→全部UID；复用既有构模、canonical/native及物理/锁定审计。新结果类型与policy隔离旧入口，当前小时逐项绑定而固定policy可跨小时接续。资源派生源码纳入身份，最终状态构造失败保留已返回阶段和known calls，pipeline无完整返回仍记unknown。

最终36项通过（39.52秒）：21 UID合成reference完成23阶段、actual完成22阶段，确实跨越旧20调用cap；两类选择均验证连续两小时。此前旧selector/core及资源相关184项回归通过（69.97秒）。两项独立pre-seal finding已修复并复核闭合，git diff --check通过。未运行H25 selector/episode，也未改变旧预算或结果。

下一实施项为该内核的持久调用记账及资源监督连接，再接episode角色映射/事务；actual:0..3尚须由business arm cursor验证，normal来源/最优仍由上游证明。当前durable tracking/hard resource enforcement/formal/security均false，不能据合成接口通过启动真实完整任务。
## 2026-09-28 selector完整调用持久记账

新增scale_selector_store.py和docs/model_spec/rq2_scale_selector_store_v1.md，复用本地NTFS lease，独立SQLite schema。数值内核前持久化覆盖全部有序阶段的intent并exact回读；返回完整typed结果后归档、摘要核对并exact回读。pending_unknown不能推为零调用，重开仅允许inspection，不重试/resume。intent存在即全额charged calls/solver seconds占用，早停不释放。returned_unverified只代表记录一致，不作数值回放或原生认证；原selector返回flags保持。

最终18项通过（19.02秒），含进程intent后exit17、intent/result INSERT no-op、提交/回读/确认失败、codec漂移、结果请求错配、早停全额charge及复制root拒绝；相关复用lease回归5项通过（20.87秒），此前与selector组合47项通过（51.43秒）。两项pre-seal finding及计费字段缺口已修复，限定独立复核闭合。git diff --check通过；未修改旧core/store/结果。

下一项接进程资源监督：明确wall/commit硬限制、终止后Job静默、再检查落盘状态及归档资源；当前无硬资源执行保证、无真实H25 selector/episode或正式准入。normal最优性和科学/数据门继续开放。
## 2026-09-28 selector固定worker与Job边界验证

新增scale_selector_worker.py和docs/model_spec/rq2_scale_selector_worker_v1.md，固定CLI接收有SHA pin、类型白名单、完整字段及结构/字节上限的canonical请求，创建一次性selector store。实现pin覆盖reference selector等依赖；回执exclusive写入后核验长度、文件身份、exact回读及最终源码/请求。回执失败保留store证据，不提供重执行或恢复授权。

17项worker测试通过（16.40秒、exit0），包括reference/actual真实tiny Windows Job及回执no-op/短写/错误字节/读取失败；进程期限、reserve停止及后代静默4项回归通过（2.07秒）。两项独立pre-seal finding已修复并限定复核闭合，git diff --check通过。Job测试只证明合成小例的执行边界，不证明H25、完整资源或正式环境；输入重建不认证normal/前驱来源。

下一项为复用现有监督工具的持久父控制器：释放前启动意图与PID/creation-time登记，停止后整Job静默，随后验证回执及store；再接episode四臂角色和跨小时事务。尚未完成父控制器、真实规模全episode、normal最优性或科学/数据验收，formal门保持。旧冻结协议、结果及所有无关未提交文件保留。
## 2026-09-28 selector持久父控制器

新增scale_selector_controller.py、对应测试及docs/model_spec/rq2_scale_selector_controller_v1.md。复用NTFS lease和既有Windows Job owner，持久请求/intent后创建suspended child，PID/creation-time登记和全链检查完成才release；wait确认整Job静默后读取回执及store，核完整request、result identity/status及inspection。新root一次性，失败保留记录，不重执行。资源声明先绑定现有父目录，实际Job再绑定新建archive/scratch。

controller与worker组合23项通过（28.55秒）；独立pre-seal的早期lease异常覆盖、terminal后的检查及receipt字段inventory三项已修复，controller最终11项通过（25.10秒、exit0），限定复核闭合。git diff --check通过。状态仍returned_unverified，不是数值接受或完整资源认证；锁释放/I/O异常保留不确定性。

下一项为新ScaleSelectionResult落盘记录的独立数值回放，再接四臂/跨小时事务。旧selector_replay、episode_coordinator、hourly_transaction均绑定旧结果类型/预算，不能直接放宽旧门。父控制器整体wall/内存/目录大小验收、真实normal最优性、完整episode和科学/数据门仍开放；未启动H25或正式实验，旧冻结协议及结果未改。
## 2026-09-28 完整UID归档数值回放

新增scale_selector_replay.py、对应测试和docs/model_spec/rq2_scale_selector_replay_v1.md。在外部record SHA、实现pin及完整request下，以既有纯native replay核和固定构模函数复核每个selected阶段的结构、版本/options、赋值、界、残差、目标锁与物理witness；完整stage与最终state/result逐字节重建相等。未调用solver或放宽旧public预算类型门。unresolved只报告未重放，不生成后继；public仅返回诊断，不授予resume/native真实性/formal权限。

12项针对性测试通过（23.62秒），另21 UID/23阶段真实store回放1项通过（18.74秒）；旧selector/native replay相关158项回归通过（98.92秒、exit0）。限定独立pre-seal无待修实质finding，git diff --check通过。篡改赋值/界、partial、阶段次序/目标锁/截断前缀，即使重算摘要也不能伪造selected。

下一项为将经核验的落盘结果接入新四臂事务适配，保留旧episode exact-type门；还需跨小时链、整体资源验收和真实normal最优性。归档相对输入一致不等于真实观测、数据库来源或工程认证；科学/数据和正式运行门保持，旧协议与结果未改。
## 2026-09-28 四臂回放结果的分阶段事务

新增scale_hourly_transaction.py、测试与docs/model_spec/rq2_scale_hourly_transaction_v1.md。完整reference回放形成精确共同请求；固定NETWORK/CFE/JOINT/B6→actual:0..3，复用capacity policy产生业务candidate及实际功率请求，actual归档回放接受后才成对返回业务/电网后继。拒绝和unresolved保留旧已提交状态并halt；CFE服务适用性与物理检查分开。跨小时绑定common前驱、source audit、mapping、业务policy及actual policy。

初轮6项25.28秒通过，两小时债务累积/恢复2项18.45秒通过；与旧事务/映射组合69项75.80秒通过。独立pre-seal发现业务policy未显式固定，已补business_policy_identity和origin_identity及替换反例；修复后最终9项44.91秒通过（exit0），限定复核闭合，git diff --check通过。两个小时验证债务由1/3到2/3或在高于baseline的恢复功率下下降，原状态保持不变。

下一项为完整episode owner串接这些纯事务与受控selector执行，检查共同曝光下四个不同arm、唯一消费及全量预算，持久提交跨小时cursor。当前只有纯内存分阶段接口，未完成磁盘原子episode、整体资源或真实normal最优性；normal来源、右删失及科学/数据门仍开放。未运行H25或正式实验，旧冻结接口/协议/结果未改。
## 2026-09-28 受控四臂episode端到端开发链

新增scale_episode.py、测试及docs/model_spec/rq2_scale_episode_v1.md。新NTFS独占owner固定连续窗口、规范四臂、同源physical origin/业务机制/actual policy与资源声明，按完整reference+四actual预留calls/solver seconds。每小时先持久intent，再通过现有父控制器逐Job执行，静默后收集归档并回放；全部臂结果准备完成才写hour result并发布内存cursor。失败poison、无重试/恢复入口；halted臂跳过执行但不释放预留。

hour result持久保存五phase evidence及消费文件pin，task/archive双lease覆盖读取、pin和crosslink；实现闭包固定worker/process/resources/lease/native replay依赖；环境只保存private copy摘要，close与advance共用guard。独立pre-seal的证据关联、读取窗口、依赖闭包与环境值问题均已修复，限定复核闭合。

最终15项通过（152.28秒、exit0），含第一小时五Job、第二小时四Job（已halted CFE跳过），累计仍预留22calls/22solver seconds，JOINT债务1/3到2/3；late failure不发布小时，消费归档改动、读取至pin之间替换、传递依赖漂移和环境变化均拒绝。git diff --check通过；旧reference_selector/actual_dispatch_selector/continuous_grid_candidate完整SHA仍匹配既有记录。测试仅pytest临时目录，无H25或正式运行。

下一必要项为已落盘整episode的独立离线核验，覆盖完整输入/phase证据/跨小时cursor和未知中断，不授予resume；另有整任务wall/内存/磁盘资源验收、真实normal最优性及科学/数据/right-censoring门。合成端到端链已接通，正式就绪仍未证明，旧协议与结果保留。
## 2026-09-28 完整episode离线核验

新增scale_episode_replay.py、测试及docs/model_spec/rq2_scale_episode_replay_v1.md。外部typed输入窗口及header/有序intent/result SHA、audit实现pin共同约束只读核验；固定五phase目录，task/archive双lease核文件与controller/receipt/store交叉链，独立重算worker命令、环境/host/process身份，检查启动和正常退出记录。纯回放重建reference共同请求、四臂与跨小时状态，完整hour body须一致；不反序列化可执行cursor，不启动Job或solver。

完成小时拒绝额外/跳过却存在的task目录；末尾pending intent保留unknown并全额charge，不打开其子DB。unresolved阶段数值细节未重放，单列报告；观察窗口消费完不等于完整履约或恢复完成。

9项通过（117.43秒），含连续两小时核验及重hash篡改反例。独立pre-seal的process身份/记录一致性、子task inventory问题修复后，最终相关6项通过（40.67秒、exit0），正常前缀与5类联动重hash进程记录均覆盖；git diff --check通过。旧episode执行器与冻结成果未改，所有测试仅合成/tmp，无H25或正式运行。

下一项集中核对完整episode的整任务资源验收缺口，并接入已有资源合同；真实normal最优性、实际数据/机制参数、末端右删失和正式科学验收继续开放。现有小例执行与离线核验链已具开发证据，正式就绪仍未证明。
## 2026-09-28 Episode资源声明与采样检查收尾

现有TaskEnvelope已接入scale_episode_resources.py、episode owner和离线核验：完整窗口五phase预留、父header/小时intent/result空间、累计wall/working set/archive/scratch/tree及host headroom检查。owner和离线核验拒绝elapsed、lifetime peak、保留字节与条目倒退；host可用commit允许波动。开发规格见docs/model_spec/rq2_scale_episode_resources_v1.md。

验证：episode执行与离线核验组合29项通过（285.39秒）；单调性修复后资源边界、传递依赖漂移、在线/离线连续两小时及完整前缀共32项通过、21项未选择（118.67秒、exit0）。命令为compute Python -B -m pytest -q -p no:cacheprovider，最终选择三个test_rq2_scale_episode*_v1.py中的resource/dependency_drift/two_hour/complete_prefix。独立pre-seal代码复核已确认五项单调性修复；未产生official verdict。git diff --check通过。

本项只完成声明与采样拒绝条件，不完成整任务资源认证：父进程硬wall/commit、最终写入关闭及离线audit成本、完整任务清单与SerialResourceBudget绑定仍需证明；记录未保存历史disk free/volume requirements。hard_parent_wall_limit/hard_parent_commit_limit/hard_disk_quota/whole_task_resources_verified均为false。

当前主线状态：多日状态、恢复债务、四臂策略及拒绝动作已有开发产物，合成执行与离线回放链已具验证。下一项先核对完整任务资源验收矩阵，复用现有监督组件并明确剩余解除条件；真实normal最优性、实际观测与机制参数登记、右删失和科学验收保持独立阻塞。不得用新增局部测试替代这些条件。未启动正式实验，旧冻结协议、结果及无关未提交文件保留。

## 2026-09-28 完整资源连接核对与嵌套监督验证

已在docs/model_spec/rq2_execution_resource_contract_v1.md补完整执行验收矩阵。确认selector预算工厂能重算合同，但episode当前仅比较传入摘要相同，尚缺原始normal/episode/envelope/serial声明与实际窗口重新绑定；此项先于外层执行入口。normal_task_process的3600秒开发上限不能直接承载H25完整预留，父episode加inner Job及独立offline audit成本也不能遗漏。wall为轮询终止，不是OS硬wall quota。

新增test_nested_task_job_membership_and_outer_quiescence的正常/停止两个短案例：使用既有normal_task_child嵌套，不增加监督框架；IsProcessInJob证实inner属于outer，持有同一HANDLE核验外层停止后inner死亡，正常报告和outer/inner peak关系均检查。首轮测试专用256 MiB父导入MemoryError已定位，测试改用768 MiB process/1 GiB Job及单线程后通过；这些数值不是正式预算建议。运行代码、旧cap、冻结配置与结果未改。

验证命令：compute Python -B -m pytest -q -p no:cacheprovider tests/test_rq2_normal_task_process_v1.py。新增两项5.19秒通过；整个文件36项8.91秒通过、exit0。独立限定pre-seal未见实质finding；无official verdict或资源认证。下一项为原始完整资源声明的episode绑定及离线重算；真实normal最优性、数据/机制身份、删失及正式科学验收仍开放。未启动solver或正式实验，未清理工作区。

## 2026-09-28 原始完整资源声明绑定

scale_episode_resources新增EpisodeResourcePlan；episode owner和离线核验强制携带原始normal/episode/envelope/serial声明，在创建或读取root前重新核算。实际完整小时窗口、source audit的normal身份/split/UID/可见信息、五role预算、总调用与秒数及envelope须匹配；task Job声明覆盖父controller加inner Job，全局commit/disk reserve至少覆盖运行时reserve。header保存完整原始声明，offline从独立typed输入重算并比较，不接受仅一致的摘要。

验证：单小时五Job1项26.93秒通过；plan/resources组合35项8.38秒通过；episode与offline完整回归30项291.96秒通过。独立pre-seal发现全局reserve与局部runtime未关联，已修复并新增两反例；最终plan正反例、完整离线前缀、重hash原始plan header篡改共16项通过、12项未选择（39.30秒、exit0）。命令均为compute Python -B -m pytest -q -p no:cacheprovider，相关文件tests/test_rq2_scale_episode_plan_v1.py、tests/test_rq2_scale_episode_resources_v1.py及tests/test_rq2_scale_episode_replay_v1.py；完整回归使用test_rq2_scale_episode_v1.py与test_rq2_scale_episode_replay_v1.py。

此项证明调用者声明与实际episode内部一致，不证明研究任务全部列齐、完整normal源范围、normal复用或最优性，也不把owned source audit提升为真实观测。独立offline仍需单独资源预算与受监督入口；下一项复用既有Job原语接固定episode/audit worker及封闭transport，覆盖父进程、最终发布/关闭与离线核验成本。3600秒开发cap、真实normal最优性、数据/机制参数及右删失/科学验收仍开放。未启动正式实验，旧冻结协议、结果及无关未提交文件保留。

## 2026-09-28 Episode固定transport与执行/审计worker

新增scale_episode_transport.py、scale_episode_worker.py及对应测试；规格见docs/model_spec/rq2_scale_episode_worker_v1.md。输入固定初态/四臂/窗口/原始资源计划白名单，支持精确Fraction和finite hex float，16MiB/64层/500000节点限制；canonical roundtrip后复验初态和资源绑定，不恢复结果或可执行后继。环境值不写入packet，仅从继承环境及指定目录重建后核外部摘要。

固定CLI分别execute新episode及audit外部header/有序pins；复用既有owner与离线核验。测试中外层Job内完成一小时五phase，再另起audit Job，四条selected数值链回放，归档全部文件hash前后相同；receipt独占fsync/回读，root及外部audit pins显式关联，全部权限标志false。request、环境目录与receipt均在evidence root外，replay要求exact顶层清单。

初轮transport22项6.23秒通过，后补embedded successor/wrong contract及直接/传递源码漂移，29项7.19秒通过；worker初轮6项58.54秒通过。独立pre-seal发现reference origin可嵌入后继carry、输入/环境可混入evidence root，均已修复。最终针对性组合16项通过、38项未选择（82.43秒、exit0），包含outer execute+独立audit、路径隔离、后继拒绝、源码漂移、extra root拒绝、正常prefix与pending_unknown。命令为compute Python -B -m pytest -q -p no:cacheprovider，文件为tests/test_rq2_scale_episode_worker_v1.py、tests/test_rq2_scale_episode_transport_v1.py和tests/test_rq2_scale_episode_replay_v1.py；最终使用-k筛选上述相关项。

receipt的pins只是owner持锁时快照；关闭后仍须独立audit与进程正常退出/Job静默。测试90秒outer不代表600秒episode声明全量可覆盖，更不认证H25资源。下一项为持久外层controller的request/intent/launch/result事务，将outer预算与完整声明绑定并计入最终写入/关闭和audit成本；3600秒开发cap、normal最优性、正式数据/机制及右删失/科学门仍开放。旧冻结协议、结果及无关未提交文件保留，无正式实验或仓库清理。

## 2026-09-28 Episode execute/audit持久外层控制器

新增scale_episode_controller.py、tests/test_rq2_scale_episode_controller_v1.py及docs/model_spec/rq2_scale_episode_controller_v1.md。PipelineBudget把同一TaskEnvelope分解为execute/audit两worker、两次quiet、controller allowance、outer metadata与两个scratch；root创建前核wall/commit/archive/scratch/条目覆盖，不借全局controller_seconds。运行时独立限制controller耗时，phase host未来空间扣除已保留字节；记录采样hard wall/commit/disk=false。

两phase分别保存intent、launch、observation和外部receipt，release前持久化PID/creation-time；只有Job quiet和exact正常观察字段、receipt一致后推进。execute保存的ordered pins进入audit intent，跨phase核episode全部证据文件身份/hash；根锁由lease检查。audit完成后在读取receipt/归档前取得episode lease并保持至final，重算完整audit报告计数，独占写result后再检查。关闭异常仍尝试释放两层lease，失败不自动重试或resume，文件存在不代表调用成功。

验证：首轮1失败/7通过定位Windows锁首字节不可另流读取，改为lease核根锁后真实pipeline1项44.77秒通过。独立预审要求controller独立计时、完整条目预留、exact进程观察及finally清理，修复后19项127.97秒通过。剩余host空间修正后4项49.36秒通过；最终锁窗口修复后真实pipeline与晚期close异常2项通过、18项未选择（87.97秒、exit0），真实测试在每次audit receipt读取时断言episode lease已被持有。命令均为compute Python -B -m pytest -q -p no:cacheprovider tests/test_rq2_scale_episode_controller_v1.py；后两轮分别用-k选择real_persistent/scratch/host_demand与real_persistent/late_evidence。git diff --check通过。

当前获得的是短合成观察窗口的持久执行和独立回放，不是完整服务或资源认证。最外层controller资源仍为采样，正式长预算及3600秒开发cap适用性、真实normal最优性、完整研究清单/数据/机制参数与右删失科学验收保持开放。下一步核对真实规模执行预算与现有开发cap的具体冲突及可复用路径，不再次开发已具证据的两phase事务。未启动正式实验或长solver，旧冻结协议、结果及无关未提交文件保留。

## 2026-09-28 外层声明预算接入与主线状态

declared_task_process.py复用旧Job生命周期，新增绑定原始资源合同SHA及TaskEnvelope的预算；scale_episode_controller支持该预算的execute/audit分配并拒绝错误绑定。旧normal_task_process及3600秒开发cap保持原SHA c7c46c08297c083338cc555a887313a94cb9e767480709caa205011b6e4d080c。校验用1秒投影保留完整内存/host需求，实际child仍使用完整新预算。仅outer接入，inner phase仍是旧短预算；不能据此宣称真实长任务或整体资源已认证。

验证命令均为D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider。tests/test_rq2_declared_task_process_v1.py与tests/test_rq2_normal_task_process_v1.py共50项通过（9.46秒）；tests/test_rq2_scale_episode_controller_v1.py -k 'real_persistent or declared_outer'共4项通过、19项未选择（97.81秒）。超过3600秒行为通过时间注入测试，端到端仍为短合成案例。git diff --check通过；未启动长求解或正式实验。

当前主线：连续多日、恢复债务、四臂、拒绝动作与诊断包已有开发产物，短合成持久执行/独立回放已接通。真实H25 normal仍只有TIME_LIMIT可行解，gap约0.125%，最优性未过；完整任务规模与内层预算、实际观测/机制参数登记、右删失和正式科学验收继续开放。下一项应直接核对这些未闭合项的可执行解除条件，优先形成normal求解及参数登记的具体任务，避免继续无边界扩展执行设施。保留旧冻结协议、结果及所有无关未提交文件。

## 2026-09-28 参数登记入口与normal前置核对

已更新docs/model_spec/rq2_continuous_multiday_parameter_evidence_v1.md：逐项关联20个未识别输入、6个未注册选择与当前代码/待登记内容，纠正早期“响应/ramp/逐笔deadline尚未实现”的范围过时说明。现有机制实现可复用，实证null和正式登记缺口保持；Google绝对功率、逐job checkpoint/抢占证据不能由聚合机制补出。代码字段之外的minimum-event-power、ramp、精度及容量声明亦明确列为待登记项。

零solver机械核对通过：20行与交付unidentified顺序完全一致、6项协议集合一致、实证仍全null/协议仍unregistered、所列代码symbol存在。input_status SHA256=263643c83cf4ec60fd25fb176f50c3aae2bd7f158f8bb550fe241f3a18d88302。旧H25 replay SHA256=b1a67d96fcda78434472440b9b31ebb9028f2f14a1bf9ec5fd00b3f8cb9df8d5，accepted_record_reproduced=false、optimality_certificate=null。首轮检查因PowerShell管道中文编码导致标题匹配失败，改用ASCII锚点后通过；未改变被核工件。

明确下一项normal前置：gurobi_ordered数值内核仍复用NormalExecutionBudget的30秒单solve/60秒总normal上限，新outer接口未覆盖它。应准备显式数值预算后继及身份/回放绑定，保留旧声明、验收精度及证据；现有15秒结果不能保证长预算收敛。科学候选还需将参数取值、单位、机制身份、窗口、事件及删失分母集中登记后审阅。此次仅更新证据索引与任务定位，未注册数值、改变科学门、运行solver或清理仓库。

## 2026-09-28 显式normal数值预算及独立回放

新增scale_normal_budget/native/kernel/replay与单线程declared Gurobi adapter，规格见docs/model_spec/rq2_scale_normal_v1.md。完整原始resource plan重新核算，绑定实际normal输入摘要、完整小时和机组清单及carry split声明；spec时限必须等于NormalWork预留。保留gap1e-8、三项1e-9容差、seed0和版本，native _solve AST与旧ordered相同。wall/working-set/payload为显式数值子分配，source/归档/离线回放整体成本仍待outer绑定。

新记录具有独立type/schema，零solver回放重算赋值、界/optimal flag、witness及调用/资源记录一致性，拒绝旧类型和重hash篡改，不返回可执行carry。新全组最终43项37.00秒通过，旧normal/native replay/resource contract相关139项57.35秒通过；600秒预算仅假solver传递，真实Gurobi仅一秒上限两小时单机小例。六个旧core/adapter/config/replay文件与H25保留索引bytes/SHA一致，git diff --check通过。

已补数值内核的长声明路径，尚未接入source-bound持久worker/controller。下一项复用已有source核验与进程监督连接该新type及回放，完整分配准备/归档/audit成本；不重建数值算法或监督框架。真实H25最优性、episode内层预算、科学参数及删失登记仍开放。没有长求解、正式运行、旧冻结修改或仓库清理。

normal数值回放限定预审补充：继承raw/witness错误从按值过滤改为逐次精确消费，防止重复错误自洽重hash后仍称一致。首轮补充用例13通过/1失败，修正raw反例使其先具有完整可回放的无效赋值后，最终受影响14项通过、31项未选择（23.43秒）。原43项是该修复前全组，不混为最终45项全组。源码、测试与准确时序见rq2_scale_normal_v1.md。

## 2026-09-28 Scale normal来源连接与固定worker

新增scale_normal_source/transport/worker，规格见docs/model_spec/rq2_scale_normal_source_worker_v1.md。复用已有prepare，执行前后重建RTS/pair并核外部assembly/binding/实现pin和完整资源计划；caller检查在kernel捕获区之外，无完整返回保留unknown调用。来源回放从当前prepare的inputs重算，并末尾再prepare。transport固定类/字段/大小，worker先intent再执行，独占记录后receipt；audit持lease、核外部intent/record/执行环境pin，并在运行时阻断四个执行入口，finally恢复。

source首轮21项83.67秒通过；修复伪错误降级后组合19项75.88秒通过；旧prepare/pair/declared相关82项94.26秒通过。最终audit guard补充后执行—审计正例及四入口阻断/恢复5项48.88秒通过。准确筛选与分批时序见规格，worker测试为合成来源下直接调用入口，不是父控制器子进程验收。

真实本地H25只读prepare、新预算绑定和transport roundtrip亦通过：25小时、158UID、原输入d9959966c52fe618e73974fc53203ad2caed5169bd7f360fc79e0ecafd06780c、0 solver calls、34.9373秒。诊断packet仅内存构造，资源清单只作一致性例，未发布运行配置或取得新normal结果。

下一项为持久父控制器连接：复用已具证据的Job/intent/launch/receipt原语，将source准备、normal、归档、独立audit与关闭成本绑定同一完整声明；固定worker自身不证明这些条件。真实normal最优性、episode内层预算、完整研究清单及机制/删失科学登记仍开放。未启动长求解或正式实验，旧冻结协议/结果及无关未提交文件保留。

## 2026-09-28 Normal父控制器审计语义修复（端到端验收未完成）

scale_normal_controller.py已形成草案，复用现有进程监督和execute/audit事务。当前完成的限定修复：不完整normal返回或调用计数未知时输出normal_invocation_unknown_not_replayed，保留solver_calls与call_count_complete原值及完整reserved_solver_seconds；只有完整数值记录可进入replayed分类。父端独立调用source.audit_source，逐字节比较完整审计报告，防止嵌套native_replay被自洽改写；父端回放封住四个求解/执行入口并在finally恢复，耗时计入controller allowance。request以packet SHA进入controller identity，修正identity encoder不支持bytes的问题。

验证：D:/Miniconda3/envs/compute/python.exe -B -m pytest -q -p no:cacheprovider tests/test_rq2_scale_normal_controller_v1.py，17 passed in 31.10s。覆盖missing-return、TIME_LIMIT类未接受状态分类、完整预算保留、真实一秒上限合成normal的零solver父端回放、嵌套报告篡改、四入口阻断及恢复、预算不足拒绝和identity绑定。测试没有启动父控制器子进程，不代表完整pipeline或真实规模验收。

下一项是该既有控制器的短合成子进程execute/audit联通与失败窗口测试；完成前不进入依赖它的真实长任务。真实H25最优性、episode内层预算、完整任务清单、机制参数与删失登记仍开放。此次仅修改草案控制器、其测试及进度说明；旧冻结协议、结果、公开观测及无关未提交文件保持。

## 2026-09-28 Normal父控制器短流程验收

限定pre-seal已闭合：真实Job execute/audit合成流程及5个audit失败窗口6项通过（106.30秒）；当前controller其余19项与新旧process相关50项共69项通过（47.53秒，6项未选择）。最终字节下终态前完成全链核验，跨phase保存目录/锁及文件身份，audit读取与终态写入实测持锁。规格、准确命令与证据边界见docs/model_spec/rq2_scale_normal_controller_v1.md。来源使用显式synthetic替身，native上限一秒，不改变真实H25 TIME_LIMIT或正式数据/资源门。

下一项转向实际研究任务清单及逐阶段预算核算，先判断所选预算是否触发episode内层3600秒限制，再确定必要接口变更；同时准备normal验证和机制参数/删失登记候选。完整科学协议及正式运行许可仍开放，不宣称已能开始正式实验。

## 2026-09-28 实际清单与3600秒限制核对

新增只读核算experiments/audit_rq2_current_workload_inventory_v1.py及results/tables/rq2_current_workload_inventory_v1_non_authoritative/audit.json（SHA256 648ed752cb47f1628a2895f8d751d73a6d62719064775dafd22f2bc2fa4101fc），规格见docs/model_spec/rq2_current_workload_inventory_v1.md。四个来源/配置pin通过，实际158 UID、25小时，单episode加normal共19901次完整路径预留；20项实证null及6项未注册选择保持。

3600秒限制作用于每个selector子进程，而非整窗episode。15秒/级的reference与actual solver预留为2400/2385秒；22秒/级剩余80/102秒非solver空间；23秒/级则solver预留本身超限。未测逐级非solver成本，不能把算术余量当资源通过，也不应在正式预算尚未选定时断言必须扩接口。现有normal与episode短流程继续复用。

旧36+10=46-cell数目重算一致，但不是完整episode数。当前缺连续窗口/coupling、training容量评估清单、holdout容量策略绑定、normal复用/信息声明、pilot重试清单、完整phase和回放资源分配。全实验调用和wall保持null；不以46乘H25假装完整预算。下一项为完整科学候选的参数/窗口/评分登记内容，再据其展开逐项执行清单；normal预算候选可独立准备。

运行compute Python -B脚本及runpy机械断言，生成后两次重算bytes一致，zero solver；首次runpy暴露相对__file__路径问题，改为resolve后通过。git diff --check通过。此核对未注册科学值、修改旧阈值、执行长求解或正式实验。

## 2026-09-28 连续科学参数/窗口/评分候选

新增configs/rq2_continuous_science_candidate_v1.DRAFT.yaml及docs/model_spec/rq2_continuous_science_candidate_v1.md，明确complete_preregistration=false、全部注册/执行门false。候选以自包含sealed v5作逐字段比较，提出168h观察/24h stride、birth+24机制期限、单期预算显式7倍、新46-cell身份、具名功率/CFE机制和次级有限窗口F/S/U评分；没有把20项实证null改成机制观测，也未批准这些科学选择。

独立R4设计预审推动修正：完整未来/period合同未定义，complete target保持unbound、prefix LB仅条件命题；仅观察168h，不虚构169-192h动作预算；deadline越界未偿为U，due-hour先恢复后exact检查；明确N/A、同维已证F优先、seed非等权、独立窗口初态、非rolling周预算可集中使用及新增恢复cap/损失假设。完整protocol/schema测试、training证书与holdout绑定及计算方案仍开放，不称完整pre-seal通过。

机械证据results/tables/rq2_continuous_science_candidate_v1_non_authoritative/structure_audit.json SHA256=6ba0fc07cf551a9fc1d18952849b46e8e8ffb051dca8accb8da41e9b5c4ec884，绑定candidate SHA256=2a0e7686b9f92355dc421531c2150ecab354a8106abea54c2d2c5d25259c9051。3pins、46个唯一物化新cell及实际窗口计数通过；gzip exact重算6个raw>1小时涉及holdout三个块、10/28窗口。沿用当前source_pair整窗预验证时该10/28为U质量下界，不是服务失败率。birth1/due25的已有cohort小例确认hour24删失、hour25偿还成功；零solver。

计算关键缺口：该候选全部配对为training14644/holdout14336。若每pair-cell直接跑一次现有168h四臂episode，对应90082390272/88187731968次selector调用；这仅是特定直接展开条件算术，不是全部算法下界。不能只扩超时或擅自缩支持；下一步须审计哪些计算可在相同输入/信息/策略身份下严格复用，并形成可行计算路线与完整training/holdout证书合同，再完善科学协议。旧冻结字节和结果保留，未启动正式或长solver实验。

## 2026-09-28 计算复用及容量证书绑定边界

新增docs/model_spec/rq2_computation_reuse_and_capacity_binding_v1.md及tests/test_rq2_computation_reuse_boundaries_v1.py；现有实现未改。10项通过（14.34秒）：同reference归档改变CFE/limits/due/available后publication身份不同、重建不调用solver；物理input相同但task/resource/caps变化时原record重挂被拒绝；actual角色身份、容量改变动作及同功率不同前序状态均有直接反例。核查与旧源码一致：policy只归零source_hour，source/预算/角色身份不能因物理输入相同而绕过。

在上一候选全部pair-cell路径的条件算术中，即使每pair reference跨46cell只做一次，也仅从178270122240降至143215914240次selector调用（减少900/4577约19.7%）；没有证明该跨task复用已实现或计算路线可运行。actual业务历史通过动作影响功率，完整网侧输入相同仍需分别核来源/cursor和任务证据归属。

training→holdout当前不是漏填一个certificate SHA：capacity_policy配置明确要求training_capacity_certificate=None。后继必须绑定目标/arm/cell/完整或前缀语义、training支持及证书、注册容量选择规则、固定策略、独立holdout来源/初态和B6规划/共享执行区别。完整目标未定义前不开发默认接受机制容量的适配器。现有normal最优性与全支持可行计算路线仍开放，不将窄测试写成formal-ready。

命令为compute Python -B -m pytest -q -p no:cacheprovider tests/test_rq2_computation_reuse_boundaries_v1.py；git diff --check通过。未启动长solver、修改冻结协议/产物或清理仓库。


## 2026-09-28 拒绝后动作的跨层验收补齐

复核确认拒绝覆盖、B6共享后继、部分响应和业务/网络事务均已有开发实现，不重复建设。
新增tests/test_rq2_scale_rejection_action_semantics_v1.py的6例，验证JOINT/B6的CFE短缺及到期小时候选恢复/miss仅在网侧接受后提交；网侧数值未决时保留候选、两侧原状态及到期前账本。timeout反例明确固定有效赋值/物理见证、maxTimeLimit和唯一optimality错误，避免把残差失败误称timeout。
新增6例与既有scale小时事务9例合并运行，15 passed in 78.92s，exit 0；独立限定预审findings闭合。命令及边界见docs/model_spec/rq2_continuous_rejection_coverage_v1.md。生产源码、配置和研究结果未改；无新增真实处置观测、正式风险或认证。
该拒绝语义验收缺口已补，后续不继续扩建此支线。真实normal最优性、全支持计算可行性与训练容量/holdout证书仍开放。600s normal诊断入口仅有未完成草案；资源API需真实任务清单，禁止用虚构episode占位。本轮未启动该长任务。

## 2026-09-28 单 normal 的真实H25诊断准备

新增SingleNormalResourcePlan独立资源声明，严格单normal/单envelope、无episode；旧完整episode清单规则保持。新类型接入既有source/transport/worker/controller，不再用占位episode满足API。
已生成configs/rq2_scale_normal_h25_600s_development_v1.DRAFT.yaml及同前缀request packet。旧H25来源、初态、158 UID/25小时和精度保持，只将native预算15秒改600秒；normal envelope1500秒，任务外serial监督20秒，总声明1520秒。默认只读入口经过前后外层pins核验，不覆盖已有attempt，不重试。
61项资源/数值测试通过；controller25项通过；入口夹具修正及外层漂移反例后最终21项通过。真实H25只读source prepare34.7656秒，0 solver，input d9959966c52fe618e73974fc53203ad2caed5169bd7f360fc79e0ecafd06780c。来源核验及最终外层复核产物在results/tables/rq2_scale_normal_h25_600s_preparation_v1_non_authoritative/；旧结果25文件hash保持一致。
具体预算、准确分批测试记录、配置/packet/runner/payload SHA及只读命令见docs/model_spec/rq2_single_normal_h25_diagnostic_v1.md。新执行目录不存在，长任务尚未启动。须明确授权本次开发长求解；正式协议、全支持计算路线及training容量/holdout绑定仍开放，不宣称formal-ready。

## 2026-09-28 成对已提交状态的诊断入口

新增experiments/summarize_rq2_scale_committed_prefix_v1.py，复用旧容量诊断的精确能量/cohort汇总，只接收规模化事务ArmCursor。拒绝裸business_candidate、未提交记录、非canonical策略/记录子类、错源小时前缀及业务/网侧末端错位；只统计已提交记录，未提交源小时显式保留。不从halted推断尝试/失败次数，完整服务/风险/容量证书保持None，历史网侧archive及风险support未验证。
新18项与旧容量诊断15项合计33项通过；补端点反例后18项通过；预审record子类绕过修复后最终20项通过（17.14秒）。代码/测试/准确命令及分批证据见docs/model_spec/rq2_scale_committed_prefix_diagnostics_v1.md。旧summarizer SHA与原记录一致，旧包/执行链未改。
该薄层关闭候选误作已提交汇总的接口缺口，不替代完整episode重放或正式评分。600秒H25诊断仍待明确长任务授权，未启动；正式科学合同、全支持计算及training/holdout证书保持开放。

## 2026-09-28 已授权H25单次诊断：native optimal但严格界一致性未过

用户明确授权后执行600秒native上限的单次开发诊断，未重试。results/tables/rq2_scale_normal_h25_600s_attempt1_non_authoritative/result.json已生成：总537.953秒、execute317.266秒、audit109.719秒，两个worker exit0且Job静默，solver_calls=1。来源及独立数值回放一致；最终replayed_unresolved_normal，formal_result=false。
本次native termination/solution均optimal、赋值有效、最大残差2.788453912216937e-10，但LB1388837.9138593453比canonical objective1388837.913859345高1ULP，严格lower<=objective未过；UB1388837.9138593455，报告相对界差1.6764421631237928e-16。它不是TIME_LIMIT或不可行。9050项binary64系数/赋值的零solver精确有理点积仍低于LB，fsum也未消除差异；不能靠重求和或剪裁下界自动升格认证。
结果hash、精确诊断、资源实测与保留清单见docs/model_spec/rq2_single_normal_h25_diagnostic_v1.md及results/tables/rq2_scale_normal_h25_600s_diagnosis_v1_non_authoritative/。旧结果25文件hash未变。该项不再缺本次运行授权或长预算实测；下一必要工作转为界/目标数值一致性合同审查与针对性零solver验证，保留旧门与此次未决结果，不自动追加长求解。完整科学合同、全支持计算和training/holdout证书仍开放。

## 2026-09-28 Objective / bound 来源采集开发

新增 src/solvers/rq2_objective_provenance_v1.py 及对应测试，分别记录 direct Gurobi、Pyomo 与 canonical/exact 目标通道，以及原生/模型目标项和 referenced assignment。保留原严格界谓词、旧 runner 和 H25 未决结果。短例确认 Pyomo 对 MIP 从 ObjBound 取 lower，对连续 LP 从 ObjVal 填 lower；不将后者自动写成独立对偶证据。

组合新测试与旧 normal 回归57项通过（44.26秒）；补原生目标项、篡改及合成 TIME_LIMIT 通道后最终12项通过（1.48秒）。实际仅使用1秒上限的小型合成 LP/MIP；没有追加 H25 或正式运行。独立 sol_reviewer 服务返回 model capacity，限定预审尚未完成。详见 docs/model_spec/rq2_objective_provenance_v1.md。

下一项是预审后接入版本化 successor 的原生通道归档与回放；尚不能从旧记录补造原生 ObjVal/ObjBound，也没有闭合1 ULP问题。完整科学合同、全支持计算及training/holdout证书继续开放。用户授权已收到，不重复以一般开发许可阻塞；该采集器尚不构成正式实验准入。

补充：第三次独立预审已执行；已按finding补目标代数inventory（区别于点值）、solution status与optimal声明一致性、原生属性缺失异常分类。最终新增16项通过（1.70秒）；限定复核尚待结束。接入前还需caller payload限额与持久归档绑定，未更改旧normal验收。

限定复核结论：collector的findings 1–3已闭合，无新增实质问题；不是official verdict。H25已完成attempt的14个文件与既有inventory的bytes/hash逐项一致，git diff --check通过。后继接入、原生通道实测及可证明界处理仍待完成，不能把采集器预审闭合写成normal最优性问题已修复。

## 2026-09-28 真实原生通道已取得，数值验收修复候选

已完成一次H25原生来源诊断，复用Job监督：native600秒上限/worker900秒/1GiB；实际227.921秒、原生Runtime176.747秒、1次solver、exit0/whole Job quiet。新目录rq2_h25_native_provenance_attempt1_non_authoritative保留完整native目标/界/表达式和赋值。ObjBoundC=ObjBound=旧LB，ObjVal=旧UB，canonical=旧值；22275赋值与旧attempt逐hex一致，原生/canonical目标代数一致，排除了该记录的目标导出差异。

父端入口24项通过（8.77秒）且限定预审闭合。fresh source/model的零solver重放7项小例通过后在真实记录通过；它使用共享kernel，是独立执行而不是独立算法实现，只重算归档native通道关系，不能重获原生值。准确hash、命令、资源和字段解释见docs/model_spec/rq2_h25_native_provenance_diagnostic_v1.md。旧结果和旧严格验收未改。

领域审计确认下一修复应区分原生界排序与跨通道目标一致性：保留raw ObjBound<=ObjVal，用原1e-9检查canonical/ObjVal一致，用原1e-8检查raw界gap，保留残差/整数/来源/witness门，明确数值最优与exact数学证明不同。候选docs/model_spec/rq2_normal_numerical_acceptance_candidate_v1.md及纯条件谓词已完成29项开发测试，正在限定复核；具体R4语义授权及正式successor接入未完成。当前不再缺原生来源证据，也不应继续重复H25求解。完整连续服务合同、全支持计算和training/holdout证书仍开放。

候选限定复核已闭合：独立reviewer重跑29项通过（1.74秒），未发现新的实质科学矛盾。真实记录的条件谓词输出已单独保存在rq2_h25_native_provenance_replay_v1_non_authoritative/candidate_evaluation.json，SHA 15e7f2b58cd847ef637c8b90edb4c03ec44f8dc6afef04d74e8445dcd343f1ef；formal/normal acceptance仍false。已就“保留原容差、删除跨通道严格排序、用raw界gap及明确双零约定”的具体R4语义向用户请求授权，尚未收到回答；通用修复/运行授权不重复询问。旧已完成H25 attempt的14文件再次核验bytes/hash全保持。

## 2026-09-28 数值验收修复已获明确授权

用户明确回复“同意该数值验收修复，继续推进（推荐）”。此前关于该具体 R4 语义“尚未收到回答”的记录已被此授权更新。保留 raw ObjBound/ObjVal、原生界排序、1e-9 目标一致性/残差/整数限及 1e-8 raw gap，双零约定 gap=0，其余零目标未决；exact 数学认证保持 false。旧严格协议与原始结果保留。

正在接入版本化 normal 数值验收 successor，加入 fresh canonical 重算与连续时序 witness，并复用现有 H25 归档作零 solver 验证；不再重复 H25 求解。完整连续服务合同、全支持计算路线及 training/holdout 证书是另外的开放项，本次数值授权不自动关闭它们。

## 2026-09-28 数值 normal successor 已封存待独立审查

用户授权已落实至只读归档验收组件。完整 canonical 重算、原生目标/界口径与连续时序 witness 在实际 H25 归档通过；assessment_preseal.json SHA256=330ca678c4d31de4c765290fec62d54a87fe90a37a8b05f5c8a0ef1715255dca，numerical_solver_optimality_accepted=true、witness errors=[]、verifier solver calls=0。机制初态、非观测功率映射、未注册 coupling 显式保留；exact/security/native-auth/resource/formal 均 false。首份旧开发 assessment 保留，spec 明确其非 seal evidence。

最终窄测试58项通过（3.86秒）；相关旧 normal 回归组合96项通过（47.69秒，额外guard测试和角色元数据之前）；限定pre-seal findings已闭合。旧H25 attempt14文件bytes/hash一致。150成员生产outer已原子发布SEALED_READY_FOR_INDEPENDENT_REVIEW，路径configs/rq2_normal_numerical_acceptance_v1.OUTER.SHA256SUMS.json，SHA256=b6214eae0848d580f903191f78281b0c50ff408aca34b090e506816088812115。fresh reviewer正在审查，不先写PASS或正式实验已启动。

数值组件不改旧normal record及其strict acceptance。后续正式流程需要显式消费新证据；完整连续合同、training/holdout证书与全支持可行计算继续开放。计算路线独立审计已证明精确零L1时UID词典序后缀为常数，尚待混合native/analytic证据链实现，不能把近零当零或只凭normal generation向量跳过物理求解；详见rq2_computation_reuse_and_capacity_binding_v1.md。

## 2026-09-28 数值 normal successor official PASS

新实例只读 sol_reviewer /root/normal_numerical_official_v1 对 exact sealed outer（SHA b6214eae0848d580f903191f78281b0c50ff408aca34b090e506816088812115）给出 official PASS，无实质 finding。独立核对150成员与旧14文件hash，并fresh零solver重放H25：10项条件true、witness无错；独立58项通过3.82秒，当前组合103项通过46.72秒。结论由root原样记录于results/tables/rq2_h25_normal_acceptance_v1_non_authoritative/official_review_receipt.json；sealed bytes未改。

本次具体数值修复的授权、实现、真实归档验证和组件独立审查已经闭合，无需继续停留在1 ULP问题或重复H25求解。PASS仅覆盖retained_h25_numerical_normal_archive_only；完整正式runner的新证据接入、四臂完整合同、全支持计算及training/holdout证书仍开放。下一项应推进显式新证据接入与已证明零L1后缀的versioned selector路线，继续保留机制/观测区别、完整支持、旧结果及全部未提交文件。正式实验尚未启动。

## 2026-09-28 零L1解析后缀 core 与 replay 已实现并封存

新增 selector_zero_face、scale_selector_zero_face、scale_selector_zero_face_replay 三个versioned development模块；原selector及normal封存包不动。真实native prefix继续原数值门；只有精确零L1及逐UID generation=plan才尝试解析。实际模型repn核验双侧偏差约束、非负domain、精确零和锁和唯一激活的minimize UID目标；完整物理赋值仍按原容差另验。近零走native，prefix未通过不解析，解析失败保留prefix且无next state。

21UID合成对照原23次/new2次native调用，逐目标hex、request、物理carry相同；新记录111359字节，SHA a0081bb0f1d2b1bdaaa45f33c6ca05731b61ebbade9e04d141823405e795ad89，位于results/tables/rq2_selector_zero_face_21uid_v1_non_authoritative/result.json。对应replay逐字节重建native prefix和21解析阶段、solver0；不能外推为真实158UID命中率或wall-time。

当前core新旧selector及旧replay组合82项通过128.84秒；后加positive-request/zero-L1和20.1 binary64 exact两项通过3.88秒（core未改）。限定pre-seal findings闭合。94成员outer已原子封存：configs/rq2_selector_zero_face_v1.OUTER.SHA256SUMS.json，SHA626ca0d72cb8f05a13453c9648980a2bfeea55ef48bc093ad5bda5761d77efe1；fresh official review进行中，尚未写PASS。

范围仅mixed core+zero-solver replay。核查现有store的_validate_record仍严格要求ScaleSelectionResult，worker固定CLASSES/实现身份，controller调用旧worker；新MixedSelectionResult不能直接重挂旧归档。下一项是显式versioned store/worker/controller接入，沿用完整最坏预算、Job监督、one-shot intent、无resume和失败保持unknown的门，然后再接episode。完整计算路线、正式科学合同及training/holdout门继续开放；未启动正式实验。

## 2026-09-28 零L1混合selector core official PASS

新实例只读 /root/selector_zero_face_official_v1 对exact outer 626ca0d72cb8f05a13453c9648980a2bfeea55ef48bc093ad5bda5761d77efe1 给出 official PASS，无finding。独立核对94成员；fresh新35项通过59.75秒，fresh新旧组合84项通过133.02秒。绑定的compute/Python3.12.12中fresh跨process禁solver回放21UID归档，2native前级+21analytic阶段及全部结果字节一致，新增solver0。Python3.11.15因input/policy绑定runtime不同正确拒绝重挂，不是跨process缺陷。

root将独立结论记录于results/tables/rq2_selector_zero_face_21uid_v1_non_authoritative/official_review_receipt.json，sealed字节未改。此PASS只关闭mixed core+replay审查；旧normal包保持不变，不授权正式运行。下一项直接推进versioned store/worker/controller接入；无需重复零L1设计或21UID证明。资源与真实158UID/全支持性能、完整科学合同和training/holdout继续开放。

## 2026-09-28 混合 selector 外层执行接入已封存

版本化 store/worker/controller 与 source-bound archive replay 已实现，限定 pre-seal findings 闭合。新路径52项通过（54.05秒），旧 store/worker/controller 回归46项通过（63.00秒）。真实小型合成 Job 的 reference/actual 分别消耗2/1次 native calls，仍预留3/2完整stage；exit0、Job quiet，随后零solver回放成功。这里的输入是机制合成例，不能写成公开数据实测或完整资源认证。

132成员 outer configs/rq2_selector_zero_face_execution_v1.OUTER.SHA256SUMS.json 已原子封存，SHA e633eed51afa8c02e194470258cc45e0324565864c40868de2343088dd263a60；独立 official review 进行中。证据位于 results/tables/rq2_selector_zero_face_execution_v1_non_authoritative/，inventory SHA 057d9542f17a078da8052222b10363e14e44c3ce3d3bdcf5d76764ddc7b34fa1。root再次逐项验证新132成员、旧normal150成员及core94成员hash全部一致。

下一必要接入点已由源码确认：scale_hourly_transaction 的 request 类型、scale_episode 的 controller 与归档 pins、scale_episode_replay 的 exact result 类型、scale_episode_transport 的固定词汇仍属于旧链。后继必须显式传递外部 store_binding_identity 到归档回放，更新实现身份闭包，并保持 reference 连续历史、四臂固定策略、业务/网侧成对提交、完整最坏预算与失败后不重试。不得将新记录重挂旧类型，也不得把现有拒绝动作/恢复债务实现重做一遍。episode接入、真实158UID命中率/成本、完整科学合同、全支持计算与training/holdout门继续开放。

独立审查已完成：新实例 /root/selector_execution_official_v1 对上述exact outer给出official PASS，无finding；fresh52项通过54.47秒、旧链46项通过63.29秒，132成员及inventory20文件匹配，旧normal150/core94成员不变。独立reference/actual归档回放均接受且新增solver0。root记录见同证据目录official_review_receipt.json；封存字节未改。PASS仅关闭mixed_selector_store_worker_controller_archive_replay审查门，下一工作按上述episode接入推进。

## 2026-09-28 混合 selector 完整 episode 接入已封存

新增scale_hourly_zero_face_transaction与scale_episode_zero_face系列共6个源文件，将Mixed request/result、外部journal binding接入小时事务、连续episode、offline replay、固定输入transport、独立execute/audit worker与顶层controller。保留四臂固定策略、业务/网侧成对提交、恢复债务、完整最坏预算、pending unknown和禁止重试；离线成功observation增加与封存子控制器一致的严格复核。旧链代码不变。

测试终态分批为：事务17项通过93.40秒；内部episode/replay33项通过423.92秒；外层及补充反例93项通过441.45秒；旧事务/拒绝动作/transport回归44项通过88.47秒。批次存在重叠，不相加声称unique计数。早期episode依赖名适配错误已修正并由上述终态覆盖；没有放宽阈值或预算。限定pre-seal findings全部闭合。

完整短例交付包在results/tables/rq2_selector_zero_face_episode_v1_non_authoritative/，inventory SHA343e939663873aecfb71b48dcecb6f49f378ab561dc41a2a22debd4620b6523c，60归档文件逐项核验。合成机制的一小时reference+四臂实际native calls为(2,1,1,1,1)，仍预留11；execute30.578秒/audit12.594秒、exit0且Job quiet，5selected/0unresolved，audit新增solver0。输入准备另有2次短求解。formal、完整服务与资源认证均false，不是真实公开数据实验。

246成员outer configs/rq2_selector_zero_face_episode_v1.OUTER.SHA256SUMS.json已原子发布SEALED_READY_FOR_INDEPENDENT_REVIEW，SHA91f031bf1d51fac67439594842237389e669fd8772aa88a641fa39af067270be。fresh reviewer /root/selector_episode_official_v1正在official review，尚未写PASS。旧normal150/core94/执行层132成员hash保持。下一工作转向正式来源链消费normal数值successor、真实158UID命中率与成本及科学/容量/training-holdout合同；不得重做已覆盖的拒绝动作或把本短例当作全支持计算可行性证明。

独立审查终态：/root/selector_episode_official_v1对上述exact outer给出official PASS，无finding。fresh端到端3项通过151.79秒、binding/pending unknown/audit guards五项通过28.67秒；审查后246成员、60交付文件和旧150/94/132成员保持一致，配置member顺序与实现身份匹配。root receipt已保存于同交付目录official_review_receipt.json。PASS仅关闭本完整episode接入组件审查，正式实验尚未启动。

后继接口已定位：src/solvers/rq2_objective_provenance_run_v1.solve_once可复用通用原生通道采集；grid_information.prepare_normal_information已有完整赋值见证与逐小时计划投影。尚需版本化来源绑定，将新数值验收证据与这些投影、外部源身份及后续selector输入连起来；当前固定H25 assessment不能冒充通用正式normal输入。机制forecast/初态/功率映射继续明示，旧严格record不原地升格。

## 2026-09-28 Normal 数值证据的通用来源与计划投影接入

新增 normal_numerical_source 只读连接层，绑定通用 solve_once canonical 数值记录、外部 record SHA、source request 与机制信息声明；重建实际输入/模型、复用已授权数值验收，再独立复算静态网络、全部逐小时出力与启停、forecast/初态/planning 参数及 allowed-plan identity。超时、无 incumbent 与未决均不发布 accepted plan；不修改旧严格 normal record。现有 current-hour view 和 common request binding 已验证兼容。

新组件42项通过195.58秒、相关旧接口回归131项通过139.61秒、H25 wrapper漂移2项通过1.80秒。限定 pre-seal findings 全部闭合。已有H25归档零求解生成25小时/158UID完整计划；最终报告 results/tables/rq2_normal_numerical_source_v1_non_authoritative/h25_projection_verified.json 为588533字节，SHA eb8f51013eb4c76e8fa7641ff71aa174143fd6c42f36a8fda01413f59db1ecd9。报告显式绑定wrapper/API实现并前后复核，原初步报告保留。初态、forecast和功率映射继续标为机制假设，native历史执行认证、完整资源、exact、安全、formal及resume均false。

189成员 configs/rq2_normal_numerical_source_v1.OUTER.SHA256SUMS.json 已原子封存，SHA e216eebe557d6c7cf4d903e9665dc769548a95c45cf02a28ff7730ef927f8553。新实例 /root/normal_source_official_v1 已给出 official PASS，无finding；fresh44项通过183.49秒，H25对象及canonical bytes与封存报告一致，独立完整投影编码、network、25小时及allowed-plan identity一致。旧normal/core/execution/episode四包150/94/132/246成员hash均保持。准确测试命令与范围见同交付目录preseal_closure.json，root记录的独立结论见official_review_receipt.json。

下一必要工作是versioned normal执行来源链：当前scale_normal_worker仍固定source.run_source/audit_source及旧schema，scale_normal_controller仍固定旧receipt投影。后继应接通新原生通道采集、来源前后检查、durable intent/Job监督、独立零solver audit，并将新plan与episode初始输入绑定。此连接层不关闭该运行链、完整科学合同、真实规模全支持成本、capacity及training/holdout门；正式实验未启动。已有四臂、拒绝动作、恢复债务及mixed selector episode产物继续复用。

## 2026-09-28 Normal 数值执行与持久监督接入

新增 normal_numerical_execution/transport/worker/controller 四个版本化模块，接通原生采集、来源及声明前后复核、已授权数值验收、完整计划持久化、Job监督、独立子进程审计和父进程完整重放。replay_information 返回已重建的 typed plan，record/audit 同时保留完整 encoded plan；不是只留下计划摘要。collector 异常继续 calls=None、complete=false，保留完整预留且不重试。原 scale_normal 链及所有科学阈值保持。

主执行及controller57项通过532.87秒，补充失败窗口5项通过118.32秒，旧worker/controller42项通过259.91秒。最后补入transport的legacy源SHA和class inventory身份绑定后，两个漂移反例及direct worker/真实process端到端共4项通过73.93秒；该批与主批有重叠，不累加为unique总数。三项pre-seal findings已闭合：求解前声明漂移拒绝、完整计划归档回放、transport依赖闭包。

短例交付 results/tables/rq2_normal_numerical_execution_v1_non_authoritative/ 包含20文件，inventory SHA a7582e24860146885aa1fb818a2cb9e3a8bc5dddc96e0f2700feba9ce3366c82。该例为3小时/1UID、36变量/51约束的合成机制source/bootstrap，准备0solver、目标执行1次native、audit0solver；execute14.297秒/audit11.203秒，exit0且Job quiet，完整plan与projection一致。它不证明公开H25来源执行、全支持资源或完整服务认证。

228成员outer configs/rq2_normal_numerical_execution_v1.OUTER.SHA256SUMS.json已原子封存，SHA 62eed9c78d89cc7af614f5527ca1afc3c3859694d79c11577f21fed32d3d3494；fresh独立审查结论为下述REWORK。旧projection189/normal150/core94/execution132/episode246成员hash均保持。准确命令、阶段与测试重叠信息见交付目录preseal_closure.json。

独立审查现已给出 official REWORK，确认三项：遗漏 max_process_peak_working_set_bytes 门、完整 core payload 未受原限额约束、缺少 elapsed 覆盖 native Runtime 的检查。审查 fresh 18项通过202.32秒，228成员及旧五包哈希保持，但这些通过项不能关闭资源门。root 已记录 official_review_receipt.json；v1封存字节保留。

v2 successor 四模块以 _v2 路径接续，只恢复上述三项原接受条件。完整 core 限额覆盖 canonical record 中的数值、projection、prepared plan 和来源/资源记录；记录严格正整数且单调的 lifetime working-set before/after；计时一致性沿用旧1e-6限。说明见 docs/model_spec/rq2_normal_numerical_execution_v2.md。

v2 主批74项通过817.87秒，主批收集后新增的执行端 Runtime 反例1项通过16.33秒；pre-seal 独立4项通过68.83秒且无剩余finding（与主批/新增项重叠）。短例交付20文件，inventory SHA13410a24b2fe877898f0f6a57f49bd8e411540a9358c84bd718ebd3f1607b019；完整记录34815字节，working-set158748672→159010816字节，wall9.8594575秒覆盖native Runtime0.0009999275秒；execute18.813秒/audit14.547秒，均exit0/quiet，执行1native、audit0solver。证据仍为3小时/1UID的合成机制来源。

264成员 configs/rq2_normal_numerical_execution_v2.OUTER.SHA256SUMS.json 已原子封存，SHA475974d853c3132486c80aeb70a56edf00dbd4b59a2816d4fb2a3168b7a9dea9。fresh独立审查 /root/normal_execution_official_v2 已给出 official PASS，无finding；独立13项通过211.56秒，覆盖全部资源门、真实进程链及persistent unknown one-shot。测试后264成员及inventory均未变；相对v1零删除、零修改、36新增，旧六包228/189/150/94/132/246成员hash保持。root记录回执见v2交付目录official_review_receipt.json，完整开发命令见preseal_closure.json。此组件的执行/持久监督独立审查门关闭，episode初始来源接入可继续按下述既有接口推进。

下一接入点是来源绑定的normal归档→既有current-hour information/common request binding→mixed episode初始输入，复用现有初始化与四臂逻辑，不再重做normal数值验收或持久监督。完整科学合同、公开来源全支持计算预算、capacity与training/holdout门仍开放；机制参数不升格为观测，formal/exact/security/native历史认证/完整资源/resume仍false，正式实验未启动。

## 2026-09-28 Normal 到 mixed episode 的完整输入对应开发

新增 normal_episode_binding.py，仍为 DRAFT_NONAUTHORITATIVE。已从外部pin绑定的normal v2归档零solver重建完整plan，逐小时核对CurrentGridInformation和RequestSourceAudit；从PairDeclaration独立重建完整业务ContinuationHour及mapping，覆盖workload小时、来源标识和CFE请求。四字段完整资源计划逐字节一致，并核对normal task依赖；SingleNormalResourcePlan不能进入episode绑定。

沿用既有科学合同：reference/actual初态分别按声明重建，实际出力不强制等于normal初态；episode允许normal覆盖的连续中间子窗。reference输入/策略身份及_admit在solver前重验，disclosure逐时重放。paired baseline的精确对应只限定此bridge的适用范围，不能推广为通用CurrentGridInformation合同。设计审计由/root/normal_episode_binding_design只读完成，主要finding已落实为代码和反例。

主批5项通过278.39秒；将single-normal门前移后，新增guard/unknown/source-drift及两种合法起点共9项通过132.11秒，两批重叠2项，unique共12项。短合成normal归档经bridge交给既有mixed episode，四臂均committed，完整最坏调用预留仍为11。源pair preparation为显式合成fixture，此结果证明接口兼容，不能解释为public/H25来源执行。七个旧包264/228/189/150/94/132/246成员hash均保持。准确命令、阶段及当前代码hash见 results/tables/rq2_normal_episode_binding_v1_non_authoritative/development_checks.json。

该轮 standalone 交付时端到端来源门仍开放；后续持久接入进度见下节。规范见 docs/model_spec/rq2_normal_episode_binding_v1.md。

## 2026-09-28 Normal 到 mixed episode 的持久来源接入开发

新增 normal_episode_transport/worker/controller，完整输入包携带 normal request/archive、episode SHA 与 bridge identity；parent、execute worker、audit worker 均独立重建绑定，两份 receipt 与最终 result 保存同一报告。四臂、债务、拒绝动作、Job 监督与完整资源预留复用旧 sealed episode。

pre-seal 发现的来源读取集缺口已修复：RTS 清单及全成员，power/workload 两包清单及全成员、builder/config、power chronology 均做 SHA/identity 检查；输出隔离覆盖这些目录和文件。实际读取的文件必须列入 config members。运行期间及 release 前重验，最终完整 source rebuild 保留。真实公开包 2 个、间接文件 16 个已零 solver 核验哈希一致；完整 pipeline 仍使用明确标记的合成来源 fixture，不能据此宣称真实 H25 端到端执行。

当前字节的 inventory、transport 与真实子进程 execute/audit 合成链共 8 项通过；该批因故障测试 spy 的 context manager 用法错误停于 1 failed/8 passed（387.36秒）。修正测试后单独重跑失败窗口文件，3 项通过395.69秒：来源在 durable launch 后漂移阻止 release；execute/audit receipt 的 binding 重编码篡改分别拒绝且无最终 result、one-shot 保持。当前新增 unique 11 项通过，历史批次不重复累计。

只读 pre-seal 审计 /root/normal_episode_binding_design 未留开放实质代码 finding；它不是 official verdict。准确命令、历史测试错误及该轮字节 hash 见 results/tables/rq2_normal_episode_binding_v1_non_authoritative/persistent_development_checks.json。7 个旧包 264/228/189/150/94/132/246 成员哈希保持；完整科学合同、全支持资源、capacity、training/holdout 门仍开放，正式实验未启动。

随后保存已有短例83文件快照，inventory SHA91ab8d751338da12d66e3ad79de1b0122767ac51c2f165e62fff681cd31a4636；保存前零solver重建绑定并核对两份worker回执，execute73.078秒/audit52.234秒、exit0且whole Job quiet，5条selector链重放、完整调用预留11。快照保留原始pytest路径，不提供重定位执行或resume。518成员outer configs/rq2_normal_episode_binding_v1.OUTER.SHA256SUMS.json已原子封存，SHA7c47018cff8267575c3cbe218cc6225969c6c5c20a25e22eefd52c9f0c1d2567，状态SEALED_READY_FOR_INDEPENDENT_REVIEW；fresh /root/normal_episode_official_v1 正在审查，尚无official verdict。代码和测试在封存前后未改，规范仅调整生命周期措辞，准确冻结清单与验收矩阵见config及preseal_closure.json。

独立审查现已完成，official PASS、无finding。fresh三批11项388.81秒、7项153.87秒、2项350.37秒，共20项通过；覆盖完整normal/资源/子窗与伪造拒绝、零solver guard、完整来源inventory/隔离、真实execute/audit及release前来源漂移。审查后518成员、83文件inventory及7个旧包均保持；两条继承链412成员零修改/零遗漏。root已记录同目录official_review_receipt.json，SHA32863fdbbcd190492c315ed5ee580aad637d6a931abde088995ce2aa741a2b95。该组件审查门关闭，不继续重做此绑定链；formal、完整科学合同、capacity/training-holdout及全支持资源门仍开放。

## 2026-09-28 连续科学候选与 planner 活动边界适配核对

零solver反例确认：在现有合法 ContinuousPlanningInputs 小例中，仅将 minimum_event_power 改为科学候选声明的1e-6，即被现有“严格大于 SERVICE_TOLERANCE”门拒绝。证据 results/tables/rq2_continuous_science_candidate_v1_non_authoritative/planner_admission_audit.json，SHA564718a6947738da9f4189bcf7157a0ef70205dae523eceae52f298e005e1d57，绑定原候选SHA2a0e7686b9f92355dc421531c2150ecab354a8106abea54c2d2c5d25259c9051。此为构造适用性缺口，不是数学/物理不可行；没有调整候选值、活动阈值或旧planner。

下一适配须区分开放物理活动集合与闭下界松弛，并通过独立精确动作见证决定有效前缀可行性；仍不能把松弛incumbent当完整/因果容量UB。完整future/period目标、policy class及training到holdout证书合同继续待定义，相关限定科学设计核对进行中。

限定设计已形成 docs/model_spec/rq2_continuous_complete_target_contract_candidate_v1.md：分别列明有限登记与长期持续对象，显式完整目标量词、初态/路径兼容关系、prefix集合投影、全部支持的continuation证明及B6分离规划边界。区分任意可接受因果策略最低容量与既有固定greedy/EDF策略族；严格request-bounded响应的峰值容量条件不能推广到容差评分。当时已提交研究对象澄清，后续选择见下节；未修改科学候选YAML。

## 2026-09-28 开放活动边界开发与有限登记对象选择

新增 continuous_planner_open_activity.py 与 planner_open_activity_witness.py：独立输入类型/identity
允许 minimum_event_power 等于1e-6，闭模型标注 open_activity_boundary_outer_relaxation；
严格动作见证继续拒绝 q<=tol 的正调用及微小正恢复。边界假活动只属于松弛模型，不能作为完整或
因果容量UB；B6保持separate planning。旧代码及候选参数保持。

新33项及旧planner/witness/assignment回归共179项通过2.13秒，无solver调用。
包括两模式×四臂的新旧标准线性模型一致性、边界反例、到期恢复和身份隔离。
开发证据 results/tables/rq2_continuous_planner_open_activity_v1_non_authoritative/development_checks.json，
SHA a6d538752bee48cc0b369f69d0e4856c878a495136777bca6679911e42da16d5。
518 sealed成员、公开交付7成员、复合诊断7文件及16依赖重新核对一致。
此项目前为build-only DRAFT；原生赋值/界审计适配和official封存审查仍开放。

用户本轮明确选择有限登记合同为主对象：登记期内全部延期工作须按期履约，后续真实输入不足仍报
unresolved。已同步目标合同和决策包；这关闭主对象分支选择，不批准登记长度、机制deadline、
预算、策略类或完整科学协议。下一步需将该对象的 enrollment/follow-up 与训练证书、holdout
评分范围明确绑定。完整支持资源门仍开放，正式实验未启动。

只读预审 /root/open_activity_preseal 已闭合开发报告引用finding，未留实质实现finding。
独立目标33项通过0.69秒；含旧short-solve的相关回归251项通过3.01秒（两批重叠）。
518成员零漂移，有限登记选择未扩展为参数批准。记录见同开发目录preseal_findings.json；
这是non-authoritative预审记录，不是official verdict或运行许可。

## 2026-09-28 开放活动 planner 原生审计接入

新增 planner_open_activity_assignment.py / planner_open_activity_short_solve.py，将版本化输入、
canonical赋值和严格见证接到owned短求解流程；原数值限、原始界、逐变量原生来源、预算和单次调用
保持，normal专用数值修复未扩展。新旧类型拒绝混用，已知旧封存字节保持。

新48项及六文件相关回归共299项通过3.52秒。预审补入3小时、单事件跨空请求小时的反例：
mock和真实solver均得到松弛区间[0.25,0.25]，中间q=1e-6使严格物理见证拒绝。
这证明两类证据分离，不是不可行证明。timeout、缺解、加载/结构/选项篡改不发布区间或重试。

四臂H2真实HiGHS合成短例各1次求解、单线程、每次time limit1秒，完整快照已保存于
results/tables/rq2_continuous_planner_open_activity_native_v1_non_authoritative/；
inventory SHA034267d7fc0bc2d2e9896cfd191cfcdb6da3823fb678be52b48846d2112ede3a。
四臂松弛区间分别[.25,.25]/[.125,.125]/[.375,.375]/[.25,.25]，精确恢复见证均通过，
仅为合成机制前缀结果。development_checks SHA67e4660f994e152da29fb1b480aa014a0cba619762de57775fd74154cf9b7992。
518旧成员及原科学候选SHA保持。该接入仍DRAFT，正式独立封存审查门未关闭。

下一必要项转向有限登记合同的登记集合、follow-up支持和完整验收实现，再绑定training容量与holdout。
尤其原短验证预算H<=168，不能据此执行168小时登记加24小时follow-up；不能静默减少登记小时或
扩大预算。完整合同/支持/资源注册及正式实验门继续开放。

已用 experiments/verify_rq2_open_activity_native_development_v1.py 零solver重装并复算4份保存的
完整assignment/witness，全部逐字段一致；checker及fixture SHA、准确命令、逐臂保存/复算摘要
见assignment_replay_checks_v2.json，已由development_checks绑定。初步检查记录保持，仅v2提供
完整重现元数据。该检查不认证原生历史执行，不升级合成例为正式结果。

限定只读预审 /root/open_activity_native_preseal 已闭合上述两项补证，未留实质实现finding。
独立新48项通过1.43秒、六文件299项通过3.79秒；独立零solver回放4份assignment/witness一致，
9项开发/回放hash及518旧成员保持。预审记录见同目录preseal_findings.json，不是official verdict。

## 2026-09-28 有限登记来源支持已逐窗核对

新增 enrollment_support_audit 与零solver入口，重新从已绑定小时源包构建continuation chains，
核对固定summary/config/实现及chains身份。在待批准E168/F24/stride24条件下保留全部1,091个
边缘登记窗口：training配对14644、两源完整follow-up14040、缺至少一源604；holdout为
14336/13743/593。缺尾部的窗口不删、不跨split/seed/chain借数据，单独保存实际和所需末时。

holdout raw>1仍是6小时；登记期影响10/28个workload窗，observed follow-up-only再增加1窗，
合计11/28。原值保留。缺源比例仅是来源覆盖算术，不是失败率或U质量下界：已提前偿清的登记
cohort可能无需该尾部；来源齐全也不能据此算履约成功。RTS模拟事故/派生边缘与业务观测继续区分。

当前报告仅为results/tables/rq2_finite_enrollment_support_v1_non_authoritative/coverage_168_24_verified.json，
SHA29ba7f5662c3dee019f183104479d8fa354f726bea0e055ee456b3dd337042c4；同目录初版已在
development_checks.json明确标为superseded draft并保留。开发报告SHAc952ef7534675b936a4c2a2bd03a9a12eec773f8807ba92cd7572e2a444db38e。
新16项及相关56项通过；固定summary SHA补入后新16项复测通过0.48秒，覆盖行/计数不变。
普通R2只读审查独立56项通过3.14秒，最终fresh run与当前报告逐字节对象一致，无开放finding，
不创建official gate/receipt。规格见docs/model_spec/rq2_finite_enrollment_support_v1.md。

有限登记对象已由用户选择，E/F数值、请求评分范围、按需停止、跨follow-up预算以及策略/容量
语义仍需形成并审阅自包含合同。source coverage检查未启动solver或正式实验。

有限登记候选已形成docs/model_spec/rq2_finite_enrollment_contract_candidate_v1.md，包括全部登记
请求及birth评分、按需真实follow-up、非登记新birth持续入账、按维度S/F/U、单一不reset账期
以及training的策略量词。E168/F24及整个最长192h episode使用原建议14事件/2.8能量均待批准。

只读领域核对进一步确认容量解释缺口：现有D只限制call，strict bounded可行时D等于峰值；
GRID_EXCESS在当前闭MILP/连续恢复下也可按max(请求峰值,qmin)截断，不自动获得恢复时序
敏感的最低容量。不能以切换现有mode就宣称解决。候选提出双向物理功率容量q+r<=D，B6按
分离规划track施加，shared执行另验；解析例显示单小时恢复的D可由0.4升至0.5、两小时恢复
回到0.4。此为R4科学选择，尚未修改planner/witness/policy或授权正式运行，待用户明确审阅。

## 2026-09-28 登记期诊断收尾及双向容量授权

mixed paired cursor 登记/后续分区诊断已完成，保留全部cohort及债务，只汇总成对提交记录，不适用shortfall为None。13项通过24.67秒；只读 /root/enrollment_review 未发现开放实质finding，普通R2任务闭合。记录见 results/tables/rq2_mixed_enrollment_prefix_v1_non_authoritative/development_checks.json。该诊断不注册评分或签发容量证书。

用户已明确批准双向物理功率容量修复：保留四臂最低D主目标，D按声明D_DC归一化，每条规划track施加q+r<=D，eta仅用于工作恢复；B6仍分离规划、共享实际执行另验。此前等待容量定义授权的状态已解除，转入独立bidirectional版本开发。E168/F24/stride24、birth+24、192h账期、事件/能量预算及其他候选参数仍未批准；正式实验未启动。最新outer及518成员零漂移，科学候选YAML和coverage报告SHA与用户保全锚点一致。

## 2026-09-29 双向物理功率容量实现与预审

独立bidirectional版本六模块已实现planner、严格witness、assignment/native、固定策略及mixed小时事务，四测试文件覆盖新语义。各规划track为q+r<=D，B6分离规划而实际执行只用一份shared容量。旧planner与normal数值阈值保持；新旧类型/身份隔离，拒绝不推进。

首批119项通过99.52秒。增加恢复容量/类型隔离后，新旧组合476通过、1项临时父目录fixture失败（149.77秒）；仅补测试mkdir后该项1通过12.33秒。共477项unique获得通过证据，不称整批首次全绿。只读预审独立复验该项1通过10.55秒，未留实质实现finding；要求补齐checker/inventory当前hash及本记录，现已同步。开发命令、hash与6份native快照、2份精确解析witness见 results/tables/rq2_bidirectional_capacity_v1_non_authoritative/。当前assignment_replay_checks_v2.json重建6+2份完整assignment/witness，零solver；旧checks保留且标注superseded。

解析0.4/eta0.8的单小时恢复D=0.5、两小时恢复D=0.4均有手工精确见证。H3原生浮点assignment虽然数值区间为[0.4,0.4]，exact allocation等式仍拒绝；未修补成物理认证。518旧成员和保全锚点无漂移。

当前等待补证的只读复核及封存后fresh official review。2026-09-29用户已要求修复后开始正式实验；该目标持续推进，但E/F、deadline、预算、评分/停止、training因果容量证明及全支持可行计算方案尚未注册。新类型接入到小时事务；persistent episode transport/worker/controller仍需显式版本化。下一步闭合当前审查并完成自包含科学候选、有限登记验收和完整执行接入，不能用这组开发小例直接启动未定协议的正式实验。

## 2026-09-29 后续核验：容量 PASS、CFE 合同阻塞

上段等待状态已更新：双向容量组件已封存，outer 为 configs/rq2_bidirectional_capacity_v1.OUTER.SHA256SUMS.json，SHA256=14f0ff3ea3bc98a66c1bc79ba66c644a4e97bac32a5277ce44c10801a630dfb1。fresh只读独立审查 official PASS，独立125项及相关477项通过，6+2 assignment/witness零solver复算，566成员及旧518成员无漂移。receipt见 results/tables/rq2_bidirectional_capacity_v1_non_authoritative/official_review_receipt.json。此 PASS 不注册新科学合同或授权正式运行。

持久episode五模块及测试已开发，仍为DRAFT_NONAUTHORITATIVE：118项通过633.88秒；补业务拒绝成对前状态/无actual目录/其他臂继续/离线回放，以及不一致预算入口拒绝，2项通过31.75秒。预算“允许额外余量”的预审finding经现有resource-plan精确绑定否证，撤回无必要实现修改；中间1失败、2通过的开发尝试保留记录。证据见 results/tables/rq2_bidirectional_episode_v1_non_authoritative/development_checks.json。normal来源桥接四模块、六测试仅为未验收draft，不能称已完成接入。episode尚未封存。

新科学阻塞：当前绝对CFE映射未随配对baseline w调整。exact rational零solver审计确认46/46候选cell在登记支持中都有q_C>w的training反例，足以排除当前完整请求合同下CFE相关规划账的有限D，增大D或延长期限无法修复该瞬时矛盾。network-only没有据此定性；不是solver infeasibility或正式结果。当前证据为 results/tables/rq2_finite_request_feasibility_v1_non_authoritative/necessary_conflicts_verified.json，SHA256=bd498113d2342da1237c6433c976b6fb4d963885f83515ca47f56544d635cafa；5测试通过0.09秒，领域只读复算exact-object一致。旧diagnostic及初版报告保留。

用户已选择“先审阅保留最低D主目标、完整支持的CFE映射与机制修正方案”。具体审阅稿 docs/model_spec/rq2_finite_cfe_mapping_candidate_v1.md 比较动作前锁定Rw额度、固定绝对R额度及按执行负载同比归属。A映射即使修正尺度，当前alpha/f仍存在必要条件冲突，不能承诺有限前沿。联合动作共服务或分离请求的含义、因果策略类、normal horizon与按需follow-up、E/F/期限/预算/评分及具体正式运行协议仍待决定。只继续独立开发验证与科学证据收集；依赖该合同的正式实验保持阻塞，不改变原冻结协议、20项empirical unknown或任何验收限。

证据口径补充：necessary_conflicts_verified是raw-source exact算术；审查指出它不是实际浮点/负载projection逐字回放。新增 experiments/verify_rq2_finite_request_projection_v1.py 使用现有12位half-even workload projection、float CFE及有效请求接口重放保留反例，projection_replay.json仍为46/46，0solver，最小q-w约0.00853765916；不是完整source window staging。未放宽阈值或覆盖旧报告。episode pre-seal已只读闭合，无开放实质finding，仍未seal；科学审阅稿与正式运行状态保持区分。

## 2026-09-29 normal→bidirectional 固定窗口桥接开发验证

此前“normal桥接尚未验收”的开发状态已有后续证据：四个独立normal_bidirectional_episode模块保持原normal桥接语义，只替换新transport/replay/owner及schema。六文件测试批次23项通过812.71秒（session71288，exit0），新增旧新outer type/schema互拒和依赖身份传播5项通过2.42秒。覆盖完整normal来源/资源/初态绑定、unknown拒绝、来源清单、真实合成execute→audit→parent、来源漂移与回执篡改失败窗。现有normal专属数值规则未传播到planner或selector，旧代码未修改。

证据与hash见 results/tables/rq2_normal_bidirectional_episode_v1_non_authoritative/development_checks.json，规格见 docs/model_spec/rq2_normal_bidirectional_episode_v1.md。容量封存566成员零漂移。该桥接仍为未封存DRAFT，pre-seal初审无实现缺陷，补充测试及记录正待只读闭合；它仅接显式固定window，不能解除按需follow-up/normal horizon、CFE映射A、联合服务定义及正式科学合同的阻塞。A尚未获得实施批准，正式实验未启动。

随后只读pre-seal复核已闭合：12项文件hash零不一致，28项通过证据与范围记录一致，无开放实质finding；同目录preseal_closure.json保存闭合记录，未seal及科学阻塞状态不变。

## 2026-09-29 方案 A 已授权实施：映射修复与完整训练必要条件

用户随后明确“授权实施”，解除 A 动作前共同额度 y=Rw 的实施授权阻塞。独立cfe_preallocation与source_pair_preallocated已实现exact request/surplus共用同一额度、新旧类型身份隔离、当前额度不依赖未来或动作、原活动阈值及分量/合计分类诊断；raw>1及正值投影零保留并unresolved。旧封存接口保持原字节，本组件不生成可执行旧hour，不引入新的浮点定向舍入规则。

新诊断逐cell保留全部14644条件training配对，46 cells按12个alpha/f组共享瞬时算术矩阵。当前报告results/tables/rq2_cfe_preallocation_v1_non_authoritative/training_support_verified.json，SHA256=eee1ef38b744fdf63bf51fc0a659252665f3c9322ff6fdf6a0d92f0445d0feab；初稿保留，阈值漂移门及source身份补强前后矩阵一致。alpha=.5/f=.5有14392个配对找到q_C>f*w反例、252个未找到；其余11组全14644个有反例。46/46 cells各自仍有反例，故当前全支持硬履约候选的CFE相关规划账依旧无有限D；这不是正式实验结果或failure概率。null不是成功，未读取holdout作评价，缺尾及全部来源保留，0solver。

新旧相关最终116项测试通过4.66秒，旧容量封存566成员零漂移。验收矩阵见docs/model_spec/rq2_cfe_preallocation_v1.md；开发证据同结果目录development_checks.json。当前进行R3只读预审。后续仍须决定全支持科学合同（联合服务含义、alpha/f独立依据、E/F/期限/预算、normal follow-up及因果策略类），并显式实现operational转换与身份接入。不得为获得有限前沿删支持、裁请求或松阈值；A授权不能替代其余参数和具体正式运行协议。

随后已完成预审闭合、独立版本封存及fresh official PASS。外层configs/rq2_cfe_preallocation_v1.OUTER.SHA256SUMS.json SHA256=8b2c9fae1353bb3d3cbca6a38a54d80582cda95b16f6534af8eeed2fddba9007，绑定587成员，含原566成员零漂移。fresh reviewer独立116项通过4.69秒，全175728矩阵条目exact oracle一致，真实25小时training来源staging及holdout5个原始越界行保留unresolved通过（该来源接口检查不是holdout服务评价）。official记录位于results/tables/rq2_cfe_preallocation_v1_non_authoritative/official_review_receipt.json。PASS仅关闭精确mapper/非执行source packet/条件训练必要条件audit组件审查门；上述科学合同和operational接入、正式运行仍未完成。

正式研究路线决策包已形成 docs/model_spec/rq2_post_preallocation_experiment_decision_v1.md。回查原estimands/preregistration后明确：完整training支持不是新增的任意筛选标准；失败时原协议estimand undefined，数学上的空集inf不能进入I_joint/I_sep/A_B6减法，也不能置零。当前反例意味着相关臂没有可直接冻结给原合同holdout的全支持可行训练D。已向用户询问保留当前候选准备负结果协议，或在最低D/完整支持不变的约束下依据独立业务/清洁电理论与证据重审合同。此为新的研究路线选择，不重复请求A实施授权；具体参数及正式运行均未擅自批准。


## 2026-09-29 已选择合同与参数重审

用户回复“1”对应紧邻会话选项“依据独立证据重审合同与参数，保留最低D和完整支持（推荐）”，不是早期决策表的行序；据此解除研究路线选择等待，授权依据独立证据重审合同与参数，保留最低双向D和完整支持。新提案见 docs/model_spec/rq2_contract_reassessment_v1.md：将现有负区域保留在完整alpha数学域的机制前沿设计中，区分分离承诺与物理共服务，参数依据不足保持明确。当前进行只读独立草案审查；具体theta、计算网格及正式运行包仍未注册，不能将路线选择等同于这些数值的批准。

当前沙箱对部分旧数据/结果及input_status.json返回Access denied，git所示D不能据此认定真实删除；未恢复或清理。本轮未重新证明全包无漂移。该访问限制不阻止可读文档和官方来源的合同论证，但正式运行前须恢复可验证的输入与封存依赖访问。

只读草案审阅已完成：/root/formal_training_route提供领域核对，/root/cfe_preallocation_official对最终稿SHA256=9a97d60ac208a62ed0579743bb124d086052cda0672ef5b9b682b65caef7b15b补核后无开放实质finding。已明确完整网格含零请求退化区、整体alpha可行性未证单调、B6共同available口径须登记；路线编号歧义通过引用即时会话选项闭合。此为非official文档审查，未seal、未测试或运行solver；文档diff检查通过。下一步形成自包含theta与计算协议，保持新科学取值待具体审阅。


## 2026-09-29 具体机制协议v2草案与访问复核

权限恢复后重读A包587个成员，全部哈希一致；input_status的20项unidentified仍全部null。上轮Access denied造成的不可验证状态已解除，本轮git status未再显示这些旧路径删除。未恢复、覆盖或清理旧产物，无相关运行进程。

新增docs/model_spec/rq2_finite_mechanism_protocol_candidate_v2.md及configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml，列出待批准theta、1% alpha网格、三条H1/reference/actual状态链、逐cell因果Pi、分账B6和共享实际策略、完整支持LB/UB与holdout绑定。独立物化去重19theta、1900cells、27823600 training cell-pairs；这只是提案规模，不是计算可承受证据。

领域/root/formal_training_route指出三链及Pi缺口并已修；只读/root/cfe_preallocation_official复核关闭effective mismatch、全部theta独立性及B6 actual确定映射缺口，当前无新增实质矛盾。doc SHA256=d218ad94cbf734bb7cdf5946283e17bebc82fa87b5d9bb101d9ed24e9359d364，YAML SHA256=7cc2adc392ff46e0898a50fd792223a75dbcf28a783d94792e902162a3c416d6。仅非official草案审阅；parse/计数/空白检查通过，未运行pytest或solver。

下一步闭合H1 objective/boundary/tie明细及具体科学合同审阅，再推进A operational、按需follow-up、同合同LB/UB证明与计算资源门。参数与执行开关全部false，正式实验未开始；不得把草案审查当作批准。


## 2026-09-29 H1规则补齐与具体开发合同待审批

新增docs/model_spec/rq2_h1_common_reference_candidate_v1.md，补正常成本目标、开放终端与残余dwell、逐mode唯一初态、三链原点、normal成本→UID commitment→UID generation数值词典序。canonical锁值独立重算，等式锁用既有normal residual 1e-9，不借reference阈值；保留native gap 1e-8和零目标规则。同输入决策projection冲突拒绝；完整assignment辅助量只作运行见证。v2 spec/YAML同步关联H1并补call_limit=1、time_step=1h。

领域/root/formal_training_route已核规则；只读/root/cfe_preallocation_official定点复核关闭noncommittable初态与projection/witness比较范围两项finding，当前足以提交具体科学开发合同审批，无开放实质finding。H1 SHA256=4316e240e7e64c5d74be280aa623cabad70573a6d4962c2ee2efffef9de7c464；v2 spec SHA256=d083a2eb32f1fe6bcaa0a1ece836f857527930514ce3ce5ca31c676292b07256；YAML SHA256=7401550ed85c7d9f0bde4ded450ccb2a89d38dbc7646ff1ff5fff9a7e92ef2c6。YAML解析、引用、空白检查通过；未跑pytest/solver，未改旧封存字节。本次为非official草案审阅，不是实现验收或执行ready。

拟一次审批v2的E168/F24/stride24、birth+24、单账期预算、19theta×100alpha、分离承诺/B6、因果Pi、H1及LB/UB/holdout规则，授权独立版本开发及短合成验证；资源pilot和正式运行包另有门槛。此前A和双向D授权不重复申请。


## 2026-09-30 v2已批准，H1构模首个实现闭合

用户明确“批准 v2 合同并开发验证”，具体科学参数及H1开发授权已获得。配套DRAFT YAML已同步scientific_parameters_approved及H1规则批准，完整执行/正式运行仍false；不再等待该合同批准。根保持唯一writer。

新增normal_h1_model.py和测试：逐mode唯一初态、单小时UID词典序构模、前目标严格等式锁、独立重建assignment审计(残差/整数1e-9)。stage身份仅作构模/审计用途，不冒充causal shared-prefix key；赋值审计无native最优性认证。最终110项通过13.76秒，含原normal构模回归及旧小例求解。开发中两次fixture/断言失败和后续修复记录在results/tables/rq2_normal_h1_model_v1_non_authoritative/development_checks.json。

只读/root/cfe_preallocation_official预审finding全部闭合，未独立重跑测试；当前仍未seal，无official verdict。旧A包587成员零漂移，未清理或覆盖旧产物。下一步接native逐阶段验收及前级锁值来源，然后补H1 current-source/三链发布、A operational、按需后续和完整支持LB/UB；不能把首个构模模块当作正式H1执行链。


## 2026-09-30 H1原生短求解链与离线重算

normal_h1_short_solve.py已实现完整短预算预验、逐阶段owned provenance求解、canonical重算与严格assignment审计、只由已接受前级生成锁值。沿用原normal数值predicate，原始native上下界/报告逐字保留；失败停止且不重试，collector返回不完整或异常时调用数unknown。budget实现绑定及非法返回类型finding已修，/root/cfe_preallocation_official只读pre-seal闭合，无开放实质finding（未独立重跑测试）。

新旧相关四文件100项通过17.68秒；真实等成本双机组五阶段锁[20,0,1,0,20]及doublezero规则均通过。两份合成三阶段链的6个原始native报告保存至results/tables/rq2_normal_h1_native_v1_non_authoritative/，另禁用solver进行6阶段离线复算一致，0calls；development_checks.json记录源码/测试/产物hash。旧A封存587成员无漂移。

该链仍为短开发组件，最多20阶段/累计60秒继承显式短预算范围；非正式controller、不验证全任务硬资源，不提供causal shared-prefix key或完整三链发布。没有修改normal/planner旧门，也未开始正式实验。下一步完成当前小时source adapter与公开decision projection、三链持久化及按需后续，再形成完整支持容量和正式执行证据。


## 2026-09-30 H1当前小时适配与normal开发状态传递

新增 normal_h1_source.py、normal_h1_current_solve.py 及独立测试/规格。静态网络提取不读未来行；当前base row与workload按250MW/12位half-even映射，中性relative clock与真实source timestamp/time basis审计分离。旧normal内核仅使用局部(0→1)索引，全部UID出力/启停与committable持续时间跨小时保留；逐mode值域、可达age及boundary/input/static/clock绑定均有检查。

完整owned native lex chain通过且carry域合法才产生nonpublished numerical candidate。容差内assignment若不满足精确carry域，返回明确unresolved、无decision；连续出力和锁值不舍入。native后输入复核或carry拒绝保留完整native证据与调用计数。原始projection改为不可变bytes，独立audit identity绑定raw、timestamp、time basis及输入，不进入共同计算键。

/root/cfe_preallocation_official只读pre-seal findings已闭合；独立运行一个零solver 5e-10边界反例，未重跑pytest/native。最终47项定向测试通过12.87秒；相关四文件回归112项通过22.53秒发生于最后postsolve证据保留补丁之前，该补丁已由最终定向测试和定点预审覆盖。此前含旧normal的171项回归通过33.70秒。两次早期测试配置错误与修复、各次范围和hash保存在 results/tables/rq2_normal_h1_source_v1_non_authoritative/development_checks.json，旧A包587成员无漂移。

本轮未seal、无official verdict、无正式实验；模块只支持同进程开发组合。后续需来源认证、精确predecessor存档回放、same-key projection冲突拒绝、原子共同发布及三链/按需后续；不能把candidate用作已发布N或完整履约证书。下一步先接共同projection存储与零solver回放。


## 2026-09-30 H1完整锁链零求解回放与共同投影日志

新增 normal_h1_replay.py 与 normal_h1_projection_store.py、两组测试及独立规格。每个stage重建模型/前级canonical锁，重跑原normal predicate和严格assignment/carry域门；owned结果权限及全部数值派生证据逐项核对，原始native报告逐字保存。回放不创建可执行boundary，也不认证历史native执行。

共同投影开发日志复用本地NTFS owner，SQLite DELETE/FULL，只追加archive与head链。每次读取一个key会重放全部witness；不同projection使该key持续unresolved_conflict，不覆盖旧投影。commit后freshconnection逐字读回已提交历史才返回成功；commit/读回异常停止本owner，按独立保留head检查恢复。原始report aggregate32MiB、全库archive aggregate64MiB在解码/取blob前检查。

/root/cfe_preallocation_official只读pre-seal findings已闭合，未独立运行pytest/solver；最终相关四文件107项通过74.95秒，含已有source/native回归。测试覆盖权限/派生值篡改、阶段缺失和顺序、auxiliary witness差异、冲突、commit前后及readback失败。冲突测试采用validator-output故障注入，不冒充第二份真实native证书。

results/tables/rq2_normal_h1_projection_store_v1_non_authoritative/ 保存一份实际3-call合成完整archive、sample_checks及NTFS日志；禁用solver后回放/幂等追加/重开一致，replay0calls。development_checks.json记录源代码、测试、示例及数据库hash；旧A包587成员零漂移。未seal、无official verdict、无正式实验。

日志当前只持久保存开发证据，不登记native invocation、不推进episode N/Rref/A head；来源认证与审计lineage、精确episode predecessor/可执行状态恢复、三链发布、按需后续及完整支持容量/资源门仍待闭合。下一步接显式episode状态与持久前驱绑定，保持已有normal数值门和reference/planner独立门。


## 2026-09-30 H1 normal 短 episode 前驱与调用持久化

新增 normal_h1_episode.py、34项定向测试及 rq2_normal_h1_episode_v1.md。独立类型/schema/application ID/head 域；normal 初态与逐小时精确前驱由日志拥有，先提交并逐字读回 intent，再调用 owned H1 链。accepted archive 完整回放、outcome 提交/fresh readback/最终历史复核均成功才返回 decision 并推进 normal；rejected/exception 返回 None，pending/halted 不重试。commit、读回或最终历史复核异常锁止 owner，需按独立核对 head 重开。

预审发现并修复了字节编码膨胀、head 域复用、归档失败泄露 accepted decision、最终回放后实现复核及提交歧义未锁止等问题。binary frame 保留 accepted archive 和失败 native payload 原字节，绑定索引/长度/hash；调用前按全部计划预算声明足够内容容量。派生失败 audit/numeric 只保留长度/hash，异常长文本是明确标注 complete 的有界摘要，不冒充完整失败回放或原生历史认证；物理磁盘未预留。

最终34项定向测试通过61.58秒；相关五文件134项回归通过129.21秒发生于最后 poison 包装补丁之前，最终定向已覆盖该补丁及新增故障窗。/root/cfe_preallocation_official只读R3 pre-seal findings闭合，无开放实质finding；独立审阅源码/测试/规格、复核hash及diff，未独立运行pytest或solver，无official verdict。

results/tables/rq2_normal_h1_episode_v1_non_authoritative/ 保存两小时合成例（6次native调用）、4条intent/outcome日志及禁用solver后重开一致证据（0调用）。development_checks.json绑定源码、测试、规格及示例hash。旧A封存587成员零漂移，原normal outer与旧science候选hash保持。未seal、未启动正式实验。

该组件只拥有normal开发状态，不认证caller-declared来源，不构成共同发布N、完整履约或最低容量证书。后续继续来源认证及共同key一致性集成、Rref/A三链发布、按需后续、完整支持LB/UB与正式执行资源门；这些尚未完成，v2总体开发未完成。


## 2026-09-30 H1 单小时固定来源对应与信息边界

新增 normal_h1_source_binding.py、32项测试及 rq2_normal_h1_source_binding_v1.md。复用固定RTS manifest/成员与source_window两侧package审计，按显式split/raw indices/seed/config pin只输出静态网络、当前base row和原始workload。真实时间、来源坐标及package/window/chain身份留在独立audit，不进入normal计算键；保持两侧独立边际时钟，不推断共同观测或pair概率。

输入端重算两份window完整自哈希并检查exact schema/type、canonical CSV坐标、实现hash和负权限；复核当前RTS行与power的index/时间/系统负载对应，读取前后再验固定文件。candidate receipt经独立expected identity驱动全来源重建才可组装H1，改字段后自行重hash不能替代来源核对。raw workload>1保留，组装仍由原mapper拒绝。

最终相关四文件121项通过21.69秒（本模块32项），包含固定真实source零solver检查、非当前信息隔离、篡改、bool/int别名和普通读入漂移。/root/cfe_preallocation_official只读R3 pre-seal findings闭合，未独立运行pytest/solver，无official verdict。results/tables/rq2_normal_h1_source_binding_v1_non_authoritative/ 保存真实training首小时audit、candidate identity及禁用solver后的重建一致检查；development_checks.json绑定hash。旧A包587成员及上一轮episode开发产物零漂移。

source_files_verified/source_correspondence_verified只证明固定内容对应；source_authenticated、selection_registered、shared_observed_clock、formal_result仍false。全年loader/package审计可以读取完整文件，算法接口只暴露当前行。无源文件writer lock或hostile ABA保证。尚未把receipt原子绑定进episode intent，也未完成登记origin/E/F选择、共同key发布、Rref/A三链、按需后续和完整支持LB/UB；正式实验未启动。下一步把来源receipt与episode前驱、调用意图共同持久化，保留已完成旧模块与结果。


## 2026-09-30 来源凭据与 H1 normal intent 同事务绑定

新增 normal_h1_source_episode.py、独立测试与规格。独立type/schema/DB/application ID/head，复用原normal数值链、binary codec与失败诊断。header绑定origin、绝对source/config路径、config pin及实现身份；step只接收独立source pin与前head，按两侧origin+completed重建来源，核对同一source chain和连续power时间。receipt identity、原始audit bytes、当前observation和normal前驱/请求/预算同一intent事务落盘；恢复只用来源重建后的当前值。source/实现漂移、提交或最终回放歧义均拒绝返回decision并锁止owner，pending/halted不重试。

最终23项定向测试通过58.29秒；相关三文件85项回归通过120.09秒发生于最后receipt gate/origin deepcopy之前，最终定向覆盖两项局部硬化。测试包含两小时合成native链及零solver重开、source/native/commit漂移和故障、篡改、来源链断裂、输入/预算拒绝与接口隔离。/root/cfe_preallocation_official只读R3 pre-seal findings闭合，未独立跑pytest/solver，无official verdict。结果记录位于 results/tables/rq2_normal_h1_source_episode_v1_non_authoritative/development_checks.json；旧A包587成员、旧episode及source-binding开发产物零漂移。

**真实资源门仍未闭合**：固定RTS有158台generator，其中73台committable，H1每小时232个native stages。实际零solver构造检查确认现20calls短门在创建episode目录前拒绝真实网络；门未放宽。192h的44544calls仅机械计数，运行时间尚未测量。real_network_stage_budget_check.json绑定来源和网络identity及拒绝证据；本组件的native通过例仍是带来源验证mock的小型合成例，不是真实RTS episode执行。

下一步需独立真实网络资源合同/零solver规模与共享键预算，保持normal科学规则和验收门；同时继续共同key发布、Rref/A三链、正式E/F来源登记、按需后续和完整支持LB/UB集成。当前来源凭据同事务的软件链已开发验证，但selection_registered/source_authenticated/formal_execution_ready仍false，正式实验未启动。


## 2026-09-30 H1 真实网络零求解规模与存储门

新增 normal_h1_resource_shape.py、normal_h1_shape_process.py 与 probe_rq2_normal_h1_shape_v1.py；规格 rq2_normal_h1_resource_shape_v1.md。独立非正式 Windows Job（60s、进程1GiB、Job1.5GiB）仅构造首/末 Pyomo 模型；固定来源双侧首小时、probe DC bus108 不构成正式样本/地点登记。末阶段231个零占位locks没有验收来源，不检查可行性；未调用solver。

真实观测：232 stages 两端均891 variables（73 binary、818 continuous），980/1211 constraints，2789/3381 standard_repn_after_fixed_substitution linear terms；Job wall5.407s，peak process commit257871872、Job259145728 bytes。只测两个模型，不推算完整native链时间或内存。结果保存在 results/tables/rq2_normal_h1_shape_v1_non_authoritative/；source/network/implementation/stage/runtime版本均绑定并独立核对。

确认架构blocker：当前每阶段16MiB原始报告上限对应单事件最坏3892576270 bytes，大于实查SQLite SQLITE_LIMIT_LENGTH=1000000000；checks显式 current_one_blob_worst_case_persistence_blocked=true。192h反事实内容753917760768 bytes超出现有短门，未实例化、未预留、未准入。正式资源合同和native时间仍null，旧20calls门保持原值。下一步开发独立分块journal/archive及总量准入；不删除raw reports或把构造测试等同正式运行。

最终44项定向测试通过7.36s；此前同实现resource+既有Windows Job回归68项通过14.14s（随后仅补测试）。旧A包587成员、此前三个H1开发记录绑定的16项文件零漂移。selection_registered/source_authenticated/formal_result/formal_execution_ready=false，正式实验未启动。独立预审状态以本轮development_checks.json为准，无production seal或official verdict。


## 2026-09-30 H1 单小时分块 journal 原语

新增 normal_h1_chunk_journal.py、tests/test_rq2_normal_h1_chunk_journal_v1.py 和规格 rq2_normal_h1_chunk_journal_v1.md。独立type/schema/applicationID/数据库，STRICT三表，复用NTFS排他lease；每块≤1MiB，元数据≤256KiB。声明payload长度/SHA、逐块hash chain、whole-payload hash、元数据hash与前驱共同绑定event head，chunks和event同事务。fresh连接流式复核完整prefix后才返回成功；commit/no-op/readback歧义锁止owner，不暴露不确定head；非重入guard拒绝活动reader期间的重入。

最终47项定向测试通过5.60s；此前chunk+旧projection store回归52项通过35.23s，之后局部身份/guard硬化由最终定向覆盖。测试实际降低SQLite单值上限，在该上限之上保存并重开3MiB分块事件，含独立hash oracle、篡改/预算/类型隔离/流中断/commit前后故障。未实际写入3.89GB或754GB，未运行真实native或正式实验。只读领域复核已明确hour-local定位；实现独立预审结论以本轮development_checks.json为准。

本原语的content_verified只证明字节完整性，物理空间/数值重放/来源真实性/formal均不认证；旧one-BLOB blocker仍适用于旧实现，完整资源门仍开放。逻辑预算不计SQLite页/index/rollback journal/temp与磁盘reserve。

下一步明确为独立full-hour stage archive/replay：单小时≤384events容纳intent+232stage receipts+terminal；每个raw报告返回后、下一阶段前先持久化。sink失败立即停止并如实报raw incomplete/U；父日志只有在指定child head完整重放与source/normal前驱再验之后才能推进小时状态。旧20-stage/32MiB replay入口与短budget身份不能直接复用或放宽；新版本复用原numeric predicate和strict audit。parent192h控制日志、共同链发布、Rref/A、完整支持LB/UB及物理资源合同仍待完成。


本轮分块原语 PRE_SEAL_AUDIT 已闭合；独立审查代理另跑47项定向测试通过5.79s，无official verdict。results/tables/rq2_normal_h1_chunk_journal_v1_non_authoritative/development_checks.json绑定源码/测试/规格及3MiB合成样例。样例零solver、独立head重开和逐块复原一致。旧A包587成员与上一轮shape记录11文件均零漂移。

领域复核补充性能门：当前append写前、fresh readback及每次iter_event都扫描完整prefix，逐stage直接使用会带来二次增长的重复I/O。后继需要独立单遍prefix replay/受控增量append协议及terminal前完整重验；不能据小样例批准232-stage wall/磁盘预算。本轮不改已审原语以弱化其检查。下一层stage顺序固定为raw返回→原数值/assignment审计→receipt原子持久化→成功后才推进canonical lock。


## 2026-09-30 H1 单小时阶段存档与流式数值重放

新增 normal_h1_hour_replay.py / normal_h1_hour_archive.py、独立测试和 rq2_normal_h1_hour_archive_v1.md。新replay-only限额≤232stage、每raw≤16MiB及独立type/key；旧20-stage/32MiB入口保持原版本。fresh模型导出阶段顺序；每份已提供raw经原numeric predicate和strict assignment audit，再chunk原子写入、fresh物理/语义readback成功后才推进canonical lock。typed报告审计拒绝保存raw并停止；模型/资源/声明错误和持久化unknown分别拒绝并锁止，不改写为数学不可行。完整terminal重算projection，部分prefix无projection。inspect在同一SQLite snapshot一次物理_scan和一次有序读，最多组装单份16MiB报告。

复用旧固定SHA的三阶段报告，零新增solver，projection payload与旧链逐字一致。新archive样例可按独立head重开。定向41项通过49.96s；相关4文件145项通过56.36s。只读R3预审闭合，独立代理另跑41项通过50.44s，无official verdict。结果及hash在 results/tables/rq2_normal_h1_hour_archive_v1_non_authoritative/development_checks.json。旧A包587成员、shape11/chunk5开发文件及旧normal outer/科学draft锚点零漂移。

真实RTS只验证232阶段声明与空stream incomplete，并确认旧短门仍拒绝；没有真实232-stage数值链/native运行。外部parent intent/source pin只是绑定引用，parent_intent_verified/source_authenticated/native_execution_authenticated/formal均false。当前写路径重复完整prefix扫描和数值重放，二次增长成本仍未资源准入。下一步优先受控增量写与collector-owned逐阶段sink，使raw落盘成为推进下一stage的必要条件；之后仍需durable parent/source-normal集成和完整物理资源合同。正式实验尚未启动。


## 2026-09-30 H1 受控增量阶段存档

新增 normal_h1_incremental_archive.py、独立测试和 rq2_normal_h1_incremental_archive_v1.md。活跃排他 lease 内使用持续 writer 的 data_version/total_changes、精确 schema/header、累计计数及 tail；当前 raw 预审、原子分块提交、保护写锁下 fresh 读回、当前 raw 二次语义审计成功后才推进 lock。提交歧义或语义恢复异常同时 poison 两层 owner。终端完整重放与缓存一致性检查保留，旧封存模块不变。每stage不再读取旧raw或重审旧stage；SQL累计计数仍遍历表，不据此声明全部线性成本或资源准入。

定向15项通过30.92s；incremental/hour/chunk相关103项通过83.98s，零新增solver。只读R3 PRE_SEAL_AUDIT无阻断项，审查者未重复运行测试，无production seal或official verdict。机器记录：results/tables/rq2_normal_h1_incremental_archive_v1_non_authoritative/development_checks.json。旧A587成员和shape11/chunk5/hour10开发文件零漂移。该模块仍只归档已有raw，source/native/parent真实性、published/formal/ready均false；真实RTS232-stage链未运行。

下一步collector必须在第一次调用前原子持久并fresh验证唯一attempt intent，绑定父/来源/当前输入、完整stage order、solver声明、旧短预算和collector/sink身份。前一receipt durable后才可下一调用；crash、calls unknown、提交不确定保留pending/unknown并由持久registry拒绝同attempt重试，不能只靠内存标志。完整child terminal验证后才能发布parent outcome。父控制器、完整支持LB/UB及物理资源合同仍开放，正式实验尚未启动。


## 2026-09-30 H1 逐阶段 collector 与 child checkpoint 开发

新增 normal_h1_stage_collector.py、测试与规格。声明保留旧短求解预算；独立registry登记intent、每stage/terminal写前checkpoint及outcome（最多n+3事件）。checkpoint机械绑定previous/expected child heads和raw/metadata SHA，child提交成功须等于预期head，再推进下一stage。给定独立registry head，重开可按checkpoint登记的两种child状态完整验证，所有pending均不续跑、不交付projection。

独立预审发现根锚点缺口，尚未闭合：registry每次更新后必须由exact typed durable parent anchor确认，才能允许后续调用、child写入或outcome交付。公开run已暂时拒绝执行，继续开发typed anchor；没有将内存one-shot标记当崩溃持久证明。只读仓库定位确认现有controller retained哈希为内存状态，可复用scale_selector_controller的xb/fsync/fresh-read文件原语和episode_store NTFS lease，但没有现成可复用根锚点。

最终11项checkpoint/故障/公开门定向测试通过66.74s，全部mock内部adapter且零新增solver。此前两事件实现的23项相关回归通过76.79s，但不外推为修改后完整回归。旧A587成员与incremental3个绑定文件零漂移。结果：results/tables/rq2_normal_h1_stage_collector_v1_non_authoritative/development_checks.json。PRE_SEAL findings仍开放，无seal/official verdict/native运行或正式实验；下一步完成typed parent anchor后重跑受影响回归和独立审查。


## 2026-09-30 H1 本地持久根锚点集成验证

新增 normal_h1_attempt_anchor.py、normal_h1_anchored_collector.py、两组测试与规格；旧collector/incremental字节不变。独立NTFS根目录明确作为local trust root，immutable编号记录xb/fsync/fresh验证，每次registry genesis/intent/checkpoint/terminal/outcome后持久锚定，再允许child/native继续。重开从anchor取得registry head，只审计不续跑；不声明退出后整个目录恶意回滚抵抗。

19项联合回归通过117.40s；同源代码后增真实子进程commit前/后os._exit测试2项通过18.82s，anchor写前/已持久确认异常与错误pin测试5项通过18.88s。R3独立预审已关闭此前根锚点与故障证据findings，审查者未重复执行测试，无official verdict。旧A587、incremental3、原collector3绑定文件零漂移。

额外运行三阶段tiny native开发例，旧预算3calls×1s；3份raw accepted，locks=(20,1,20)，7条anchor records，16.30s含I/O/构模/重放；关闭后独立末anchor SHA重开一致。结果和哈希：results/tables/rq2_normal_h1_anchored_collector_v1_non_authoritative/development_checks.json。本地短链集成已验证，非真实RTS232-stage、非hard资源准入或native历史认证。

下一步接source-normal父控制器，绑定唯一请求/跨root去重、共同prefix发布及完整资源准入；不得把该local trust root或短例解释为正式履约/容量证书。真实完整支持LB/UB与正式实验仍未完成，formal/ready保持false。


## 2026-09-30 H1 来源绑定父控制器与两小时集成

新增 normal_h1_anchored_source_episode.py、测试和规格。复用严格来源加载/链和时间连续性、旧完整短预算预留；父chunk日志仅存source audit与child引用。父intent锚定后才创建固定小时child目录；运行child关闭后先凭最终anchor SHA fresh reopen并逐字段一致，再重载parent/source、提交outcome并最终restore。before仅由完整child projection私有重建。pending/rejected不推进、不退预算，reopen仅审计。独立父namespace跨root全局去重、Rref/A共同发布仍未实现。

最终9项父测试通过178.42s；相关来源绑定/anchored collector 44项通过95.72s。R3独立预审关闭fresh reopen顺序finding，新增损坏/漂移测试保证parent仍只有intent；无official verdict。旧A587成员、上一轮anchored collector20文件零漂移。

两小时synthetic source native开发例完成6份accepted raw，逐小时completed=1、2，最终G1出力20/on age2，独立父anchor重开一致。原6calls×1s solver预算，116.14s总耗时含完整重放，不是硬wall资源认证。结果与原生provenance清单：results/tables/rq2_normal_h1_anchored_source_episode_v1_non_authoritative/development_checks.json。没有真实RTS/完整多日实验，formal/ready/source/native-auth均false。

下一步仍需完整资源准入及可扩展父级执行/共同prefix发布。当前short parent反复重放完整prefix，不能外推192h运行预算；真实232-stage执行、完整支持LB/UB与正式实验尚未完成。


## 2026-09-30 H1 有界 child 审计作用域

新增 normal_h1_scoped_child_inspection.py 和 normal_h1_scoped_source_episode.py，保留旧绑定实现与数据。构造期完整 replay 后，仅在持续连接 epoch、cache/结构/计数/head/身份验证通过时以一次性 token 供首次 inspect 消费；再次 inspect 完整重放。独立 outer audit receipt、父 adapter 内外 exact type 与七项权限 false gate、防凭据重用和新旧 parent 声明隔离均已验证。inspection-only 为 API 边界，底层仍 rw SQLite 与 BEGIN IMMEDIATE。

child 11 项通过；同轮联合测试 14 passed/1 failed（父测试临时目录缺失），修正后最终父 6 项和相关 103 项共109 passed/204.60s。独立 R3 pre-seal 实质 findings 已闭合，审查者未重复执行测试，无 production seal/official verdict。旧 CFE 587、collector20、source parent39 个绑定文件零漂移；保全锚点未改变。

零新增 solver 的同一三阶段 raw 对照中，结果逐字段相等，阶段审计12降为3次；单次 instrumented wall 6.52s降为2.57s。结果与哈希见 results/tables/rq2_normal_h1_scoped_inspection_v1_non_authoritative/development_checks.json；详细诊断见 rq2_normal_h1_parent_profile_v1_non_authoritative。仅支持局部重复审计消除，不能外推真实多日硬资源预算。

下一步仍需处理父完整 prefix 重放与依赖身份重复采样的扩展成本，完成真实232阶段资源合同、共同 Rref/A prefix 发布及完整支持 LB/UB。正式实验尚未启动，formal/ready保持false。


## 2026-09-30 H1 完整 normal 资源库存与版本化 full anchor

核对发现旧 NormalWork 按每个normal任务一次求解核算，不能直接用于每小时232阶段H1。新增 normal_h1_full_resource_contract.py，以独立typed workload和资源声明复用TaskEnvelope/SerialResourceBudget，完整登记stage/UID/solver spec，192小时为44544次；Fraction精确累计TimeLimit，分别检查task/plan wall、串行max Job commit、保留全部archive/scratch及显式overhead。bind_current_hour实际构造首/末shape，零占位locks仅用于计数，不声称可行性或未来carry。旧短预算20calls/60秒保持。

新增 normal_h1_full_attempt_anchor.py，独立schema/receipt/实现及直接依赖身份，cap385与单记录64KiB；覆盖232-stage小时236records和192h父385records。初始33项通过395.88s，含完整385循环；仅anchor identity依赖修复后，最终67 passed/1 deselected3.91s覆盖全部受影响门与相关回归，未重复未变容量循环。早期耗时不作为最终实现资源测量。R3只读pre-seal findings闭合，无seal/official verdict。

零solver runner核验旧shape11绑定文件及1+73+158完整stage结构。含child/registry/anchors/parent的内容cap上界：1h4031840256bytes、192h774088294400bytes；均非实际使用量、最低磁盘需求或物理保留。per-stage/non-solver/overhead/commit/host仍null。结果：results/tables/rq2_normal_h1_full_resources_v1_non_authoritative/。旧CFE587、shape11、scoped9绑定文件零漂移。

下一步直接接独立full collector与已有declared_task_process Windows Job controller，保留逐stage raw/checkpoint/anchor/fresh审计顺序，再形成真实单小时native校准候选包。现source parent仍受旧短预算/anchor cap，不得偷接新类型或启动真实232-stage链。完整研究任务清单、共同Rref/A、完整支持LB/UB及正式实验继续开放，formal/ready保持false。


## 2026-09-30 H1 完整 collector 与单小时 Job 校准候选封存

已接独立 full collector、full anchor 与已有 declared_task_process Windows Job；保留原 numeric predicate、strict locks 与 raw/checkpoint/anchor/fresh 顺序。worker/supervisor/full collector native 入口均要求 exact consumed gate，独立 inner/outer、official PASS receipt 与单次用户 authority 分离；partial claim 或任何失败不自动 retry/resume。Job observation 的 identity/PID/creation、quiet、资源类型/权限位及显式 licensed environment allowlist 已验证，原 typed observation 和 controller records 的 SHA 保留。

最终主代理定向87项通过235.49s；追加 inner/holdout 反例后 gate 28项通过2.56s。只读 pre-seal 审查者独立87项通过219.48s、gate28项通过2.61s，全部 findings 闭合；这些仍是 PRE_SEAL，不是 official verdict。此前未变 resource/declared-process 广泛回归包含于122项通过247.89s。真实 Windows Job 验证只消费保存的三阶段 raw，新增solver调用为0。旧 CFE587、full_resources7、shape11成员无漂移。

具体校准 request 复用 training 原点来源、dc_bus108，232=1+73+158 stages，5s/stage、3600s task、2GiB Job；archive内容cap4031840256bytes另加256MiB overhead，scratch256MiB。fresh source/shape准备实际核到891 variables、terminal1211 constraints，零solver。时间/overhead仍是待测allowance，不是完整资源准入。

canonical configs/rq2_normal_h1_calibration_v1.json SHA256=bf1a66754a69ec6f87d53dc029e88c44e0fb0e0d07648f62076d2fc9f7e62686；outer configs/rq2_normal_h1_calibration_v1.OUTER.SHA256SUMS.json SHA256=289f9b147afa7a00b1abc4ff5dc10da09b57e0920d57be0215c352ff4648438d，813成员。config/lease/evidence/inner通过xb/fsync/fresh读回，outer经非覆盖原子rename发布SEALED_READY_FOR_INDEPENDENT_REVIEW，再次verify_package及全部成员hash一致。已封存字节不再修改。

当前由全新上下文 /root/h1_calibration_official 独立审查 exact outer，尚无official verdict，claim未消费，真实232-stage native与正式实验均未启动。开发证据见 results/tables/rq2_normal_h1_full_job_v1_non_authoritative/development_checks.json（SHA256=340a9d199ce8b03d0573b7b17b32c54b86e0539891bc0bb9da858b4bf0af8a99）。旧漂移开发草案保留，只以canonical request为封存输入。完整研究资源清单、共同Rref/A发布、完整支持LB/UB与正式实验继续开放；formal/ready保持false。

## 2026-09-30 H1 单小时校准 official PASS 与首次启动

全新只读 reviewer /root/h1_calibration_official 对 exact outer 289f9b147afa7a00b1abc4ff5dc10da09b57e0920d57be0215c352ff4648438d 给出 official PASS，冻结矩阵1–8满足，无阻断finding；独立91 passed in 215.37s，退出码0，测试后813成员零漂移。该PASS只关闭review gate。

依据本次用户“修复问题，然后完成必要门禁并开始正式实验”及指定232-stage单小时校准下一步的指令，另行记录单次native校准authority，retry_authorized=false。独立review/authority/gate及启动前headroom记录位于 results/tables/rq2_normal_h1_full_job_v1_non_authoritative/。启动前commit和合并同卷disk余量满足；该快照不是预留或完整研究资源证明。记录快照后，交互脚本误用sufficient属性导致显示检查异常；读取实际observed_headroom_sufficient=true且errors=[]后继续，未重写记录、未提前consume/native。

一次性claim已消耗；2026-09-30 19:52（Asia/Shanghai）父控制器3528启动受监督Windows Job worker42132。运行根 results/tables/rq2_normal_h1_origin_calibration_v1_non_authoritative/。当前等待whole Job quiescence再读数值结果，不自动retry/resume。完整研究资源、共同Rref/A、完整支持LB/UB仍开放；正式研究实验尚未启动。

## 2026-09-30 H1 单小时首次校准终态与数值阻断

受监督 Job 已whole_job_quiescent=true，exit_code=0，elapsed=304.35899999999674s，无runtime资源错误；process/Job peak commit分别267927552/269197312 bytes。worker完成fresh reopen且逐字段一致，controller完成retained records与report检查。

本次status=rejected，stored_reports=26，其中25份stage_accepted、1份stage_rejected；published solver_calls=null、projection_identity=null，未完成232-stage小时。拒绝位于index25、commitment/201_CT_1。保存raw的native numeric predicate全部通过（gap0，maximum residual=2.6987936877750535e-12，integrality=2.668088179630103e-13），但独立H1 assignment审计复现unit_chronology严格非负错误：generation[normal,0,201_CT_2]=-2.6987936877750535e-12 MW。canonical objective hex两通道一致，不是objective mismatch。拒绝不构成数学不可行，不能放宽门限或clip后重新解释旧raw。

26份已保存raw累计2261621bytes，native Runtime字段累计3.9769997596740723s；整个run root逻辑文件大小2426133bytes（非物理分配量）。这些只是已观察前缀，不能外推完整小时/192h/全研究资源充分性。

只读零solver诊断及运行观测：results/tables/rq2_normal_h1_full_job_v1_non_authoritative/calibration_v1.run_observation.json，SHA256=dbf51a7c6cc18cb8369943094ce749bc918e99848bbcba01773dbae9ba82ff84；postrun inventory SHA256=37d55a780e7d92936a9e6d80082428293f703ed96714ba16a0b4809a5ff375ef。旧sealed包及结果保留，claim已消耗，没有retry/resume。正在只读领域诊断与独立运行证据复核；完整研究资源、共同Rref/A、完整支持LB/UB继续开放，formal_execution_ready/formal_result保持false。

## 2026-09-30 H1 校准运行证据复核与科学决策边界

独立只读post-run复核已完成：run inventory44成员和sealed outer813成员均零漂移；两个SQLite integrity_check=ok，registry28events、child26events、29条full-anchor连续；PID/creation/process identity及全部retained pins一致。零solver重放26份raw独立复现25accepted+1rejected。该复核不是新的official verdict；审查摘要见 results/tables/rq2_normal_h1_full_job_v1_non_authoritative/calibration_v1.postrun_review.json。

领域诊断确认当前拒绝符合冻结合同。rq2_h1_common_reference_candidate_v1.md第45行禁止连续量因锁定失败自行舍入或移动，rq2_continuous_grid_normal_v1.md第47–49行要求保留原generation，失败不发布carry且不clip。1e-9 residual容差不能自行变为carry-domain转换权限。修复若引入独立normalized candidate及全约束/目标/locks/chronology重审，属于R4科学规则变更；根已请求用户对generation[-1e-9,0)→0这个明确候选作出新授权，尚未实施。候选阈值不是从本次失败推定批准；旧v1拒绝结果永不改写。决策记录 calibration_v1.blocker_decision.json（SHA256=ea3031457e3f3d61da5ab95acddee824d9333927a20492753e71c51f6e732b4e）。

当前正式研究实验未启动。依赖该科学决策的successor开发与后续native运行保持关闭；既有完整研究资源、共同Rref/A、完整支持LB/UB门亦未闭合。无自动retry，无活动的校准worker。

## 2026-09-30 用户批准 H1 generation-domain R4 successor 开发

用户已明确回复“授权上述 R4 successor 开发与审查”：normal/time0 generation 的[-1e-9,0)区间映射为正零，保留raw/delta，完整约束、功率平衡、原objective hex、strict locks和chronology重新审计，任一失败仍拒绝。授权不包括新的native运行。独立记录 results/tables/rq2_normal_h1_full_job_v2_non_authoritative/scientific_development_authority.json（SHA256=447ae2cbd3161f23c1916f2bbbd1c55a382ddd8cb1ddc50b2ac44d86dc912c70）；此前pending决策记录作为历史保留。

根代理正在实现独立v2 generation helper、replay/archive/collector/resource/Job/gate链，全部v1成员字节保持。当前v2链路91项通过295.60s，规则+gate47项通过26.68s，旧H1模型28项通过2.89s；全为零native的saved-raw/合成验证。独立只读PRE_SEAL审查进行中，已指出prepare schema、diagnostic显式成功检查与强制脚本闭包问题，正在按finding修复。尚无v2production seal/official verdict/consume/native。正式研究的资源、共同Rref/A与完整支持LB/UB门继续开放。

## 2026-09-30 H1 generation-domain v2 PRE_SEAL 闭合与正式封存

R4 successor的独立PRE_SEAL findings已全部闭合。修正版诊断以python -B -O运行退出0，显式检查不依赖assert；从独立pin的旧outer及postrun inventory读取/核验旧结果，保存26raw的新candidate prefix、末阶段mapping及fresh reopen均通过。新prefix仍collecting、无projection、solver_calls=0；末阶段仅归零201_CT_2，candidate最大constraint residual5.3362e-12、power balance4.1354e-12、锁残差0，原objective仍-0x0.0p+0。诊断SHA256=124a8999651ea6ccd271e2f8c82681cd8dd50e0b9dc9860cb52b6f1de2ad8255；旧813sealed与44run成员零漂移。旧初始prepare/诊断草案保留，不作为最终门证据。

独立preseal规则19项、gate28项均通过。主代理v2链路91项、规则+gate47项、最终closure gate28项、旧H1模型28项通过；git diff --check通过。最终开发证据 results/tables/rq2_normal_h1_full_job_v2_non_authoritative/development_checks.json，SHA256=7f63a5dd8c24c1096f1af83f78091821f01ddc159fb95916bd601ec2d3acaa81。

canonical request configs/rq2_normal_h1_calibration_v2.json SHA256=00184fba4c48a6479ff69583e5eb585104fc3a878789af25c6da59f2808868d5；inner SHA256=0a69791c6721429f590698562da2e17f90cea0f6ce240970114384e1264033e8；outer configs/rq2_normal_h1_calibration_v2.OUTER.SHA256SUMS.json SHA256=79830ab6c1b31aaef41174544e472ef800674de1f76228793f30f6b87e4f6eba。895成员、331required closure，含科学开发authority、最终规格、诊断脚本与实际产物。经过exclusive写入/fsync/读回、pending验证、非覆盖rename发布SEALED_READY_FOR_INDEPENDENT_REVIEW，再次全量verify_package成功。自此不再修改成员字节。

全新上下文 /root/h1_projection_v2_official 已开始official R4只读审查。当前无official verdict，新claim与native root不存在，未启动新native。现用户授权仅开发/审查；新的单次native校准待exact package审查通过后另行确认。其余206阶段、完整projection、完整研究资源、共同Rref/A和完整支持LB/UB仍无通过证据，formal/ready保持false。

## 2026-09-30 H1 generation-domain v2 official PASS，待单次运行授权

全新只读reviewer /root/h1_projection_v2_official 已对exact outer 79830ab6c1b31aaef41174544e472ef800674de1f76228793f30f6b87e4f6eba给出official PASS，矩阵1–7全部满足，无阻断finding。独立四文件110 passed in 219.26s，退出码0；测试后895成员再次全量核验零漂移，inner894成员与331closure关系一致；旧813sealed+44run成员保全。official回执与审查证据位于 results/tables/rq2_normal_h1_full_job_v2_non_authoritative/calibration_v2.official_review*.json。

此次PASS只关闭独立审查门。用户本轮R4授权限于开发、测试和独立审查，尚无新native权限；新claim与root仍不存在。待确认的具体动作是该exact包的一次training原点native校准：232stages、单线程、每stage5s、总task3600s、2GiB Job，raw/失败结果全保留，不自动retry/resume。完整projection、完整研究资源、共同Rref/A及完整支持LB/UB仍未闭合，正式研究实验尚未启动。

## 2026-10-02 H1 v2 单次 native 校准获授权并启动

用户明确“确认启动”。启动前git status/相关进程检查完成，无冲突运行；exact outer 79830ab6c1b31aaef41174544e472ef800674de1f76228793f30f6b87e4f6eba的895成员及official PASS回执复核通过，claim与root起初不存在。单次user authority SHA256=d7c7cb576a365f0c2431c4a238a65015d3a3dfe5c5ebc9d85ae8cbdb1205f9d1；execution gate SHA256=808801c8d5fdfd2281fdade1a009beb640c3d259b5b6fa48162c993816ceea8e。资源余量快照满足，记录在v2开发目录calibration_v2.prelaunch_headroom.json；不是物理预留或完整研究资源充分性证明。

单次claim已消耗，父控制器PID30156、受监督Windows Job worker PID5260已启动，运行根results/tables/rq2_normal_h1_origin_calibration_v2_non_authoritative/。参数保持232stages、单线程、每stage5s、task3600s、2GiB Job；不自动retry/resume。等待whole Job quiescence后才读数值产物。本次为单小时native校准，完整研究实验及资源、共同Rref/A、完整支持LB/UB门仍未完成。


## 2026-10-02 H1 v2 单次校准超时，完整 raw 已保留但终态未提交

本次授权运行已结束，父控制器退出码1；Windows Job记录 reason=task_deadline_stop、elapsed=3598.0469999999914s、worker exit_code=57346、whole_job_quiescent=true。原task3600s含2s quiet预算，时限没有延长。无runtime资源余量错误，process/Job peak commit分别263905280/265134080 bytes。claim永久消耗，没有retry/resume；相关native进程已结束。超时不是数学不可行或数值拒绝。

只读提取确认child保存232份stage_accepted raw、0份stage_rejected，raw累计19438785bytes；两个SQLite integrity_check=ok，逐raw长度/SHA匹配。registry有234events（1intent+233checkpoints）、full anchor有235records；最后预登记child event233为空payload的terminal checkpoint，但child中只有232stage events，无accepted_terminal，无attempt_outcome，worker_result.json及job_checks.json均缺失。因此本次仍为unresolved/pending_unknown，published_solver_calls=null、projection_identity=null；不能用完整raw库存替代终态、fresh reopen或Job成功门。

232个raw内native Runtime字段累计7.084001064300537s、最大0.745999813079834s。仅1个stage对1个generation作批准范围内映射。保存receipt中的candidate最大constraint residual=4.533475816970167e-10、power balance=4.9965365178650245e-11、lock residual=2.764863893389702e-10。这里是保留证据的提取，独立数值重放另行核验；不能改写旧运行状态。总耗时主要位于native Runtime计时之外，代码在完整阶段之后仍执行多轮完整重放；当前证据定位到terminal checkpoint已登记而child terminal未提交，缺少中断栈，不能指定精确被中止函数或定量归因。

postrun inventory：results/tables/rq2_normal_h1_full_job_v2_non_authoritative/calibration_v2.postrun_inventory.json，SHA256=281ad90c2da8bdb2ff0a1031d94379f2887dc663f235c52619a1c75e25521fb4，248files、logical20931567bytes（不是物理分配量）；运行观测calibration_v2.run_observation.json SHA256=ff23cbead74ff468039db97aaa11971f6f5f73b9bfa606c4314377eafd2e6e69。sealed outer895成员零漂移，exact consumed gate再次核验通过，git diff --check通过。独立只读post-run evidence audit正在进行，不生成新的official verdict。

后续需先对零solver重放/持久化开销作隔离诊断，再准备有完整性能与失败窗口证据的versioned successor；旧v2包和运行根不修改，不补写terminal、不延长旧lease。新native启动须有新的可审查包和明确运行授权。完整研究资源、共同Rref/A、完整支持LB/UB继续开放，formal_execution_ready/formal_result均false，正式研究实验尚未启动。


## 2026-10-02 H1 v2 post-run 独立复核闭合

只读reviewer /root/h1_projection_v2_official 完成post-run evidence audit（不是新official verdict）。895sealed成员和248run文件零漂移，两个SQLite完整hash/chunk/predecessor链、234registry events、232child stages、235anchor records及全部绑定通过。一次且仅一次完整232-stage零solver重放退出0，wall309.4148276000051s；全部stage约束、locks、功率平衡与最终transition重审通过。重建候选projection identity=382ec2bea1674f24b144afa74151c69cba2b780c1a240a5ed72d99a111908121，payload SHA256=034d14eb5728732790177a2f76af7fa552d9a7dad56ecfbfaf43d217eb7b2cc9（8799bytes）；重建terminal metadata SHA256=cef09d5f29cc687fd2e31d08421a65c6a067a21b617e5acf76b91147afcdf67f与拟child head=4b0b9baa8ce614c2a246f89e05fcf41b32f7d712d5263d333619795182672dff均匹配registry最后checkpoint。

这证明保存raw可重建完整候选projection；原child terminal/outcome/worker_result/job_checks仍缺失，本次status仍unresolved_task_deadline_stop，不能补认Job成功、发布projection或解除资源准入。独立审查摘要calibration_v2.postrun_review.json SHA256=9c034035f67bc8d891d966d19b5fd6e5f90ea8443c58949e19e9c93273c16cf2，位于results/tables/rq2_normal_h1_full_job_v2_non_authoritative/。

额外零solver单stage231 cProfile诊断：calibration_v2.saved_stage_profile.json SHA256=94cdb129edb172bb2add3eb6971df839ee17873bb3451ad81c4b0100457a7595。单次audit wall2.6078496s，normal_input_identity调用18次、H1构建4次、底层模型构建6次。独立审查认可其支持重复模型构建/identity计算为该stage热点的质性判断；它带profiling开销且与只读重放并行，不是全任务benchmark，不能定量外推总耗时。原run248files再次核验零漂移，无native活动进程，没有代码/阈值/资源上限变更。下一步先以保存raw对性能successor作隔离开发与完整一致性/失败窗口验证，再封存和独立审查；新native运行另需明确授权。完整研究门继续阻塞。


## 2026-10-02 H1 性能 successor v3 开发与整链验证

用户要求“什么情况，解决下问题”，按R3开展独立v3性能修复，根唯一写入，旧v2封存和运行根保留。只读PRE_SEAL reviewer /root/h1_perf_preseal 已审查数值等价与失败边界；raw/candidate窗口阈值漂移、离线benchmark预算门、完整projection payload核验和旧run输出隔离等findings已修。每次_audit_stage的H1构建由4次降2次、底层构建由6次降2次，raw/candidate各自完整检查，fixed基准保存，legacy residual临时排除H1 locks且finally恢复，chronology独立重验，v2 scientific rule identity保持。terminal/fresh-owner完整重放及一次性门禁保留。

最终v3四文件137 passed in247.66s，退出0；相关旧v2规则与H1模型47 passed in24.88s，退出0。初轮123pass/1failure是缺变量测试fixture在被测入口前抛KeyError，已修正测试入口；没有放宽实现检查。测试明细results/tables/rq2_normal_h1_full_job_v3_non_authoritative/development_test_results.json。

初次离线草案诊断在18份raw后为修复脚本门禁主动停止，全部文件保留，不作为完整证据。修正版用python -B -O在final_saved_worker_non_authoritative新目录运行真实232-stage saved-worker，禁止native，逐次比较v2 numeric SHA、lock hex、mapping receipt，并要求完整terminal payload一致和offline wall<2440s；当前尚在运行，未封存、无official verdict和新native权限。完整研究门继续阻塞。


## 2026-10-02 H1 v3 clone 与完整 snapshot 复用修复

上一版 saved-worker 草案为继续性能修复主动停止，保留172份child stage及173个registry events，未完成terminal，不能作为性能通过证据。停止记录为 results/tables/rq2_normal_h1_full_job_v3_non_authoritative/second_saved_benchmark_stopped.json。

当前每次stage audit改为一次canonical构建加独立clone，运行时复核变量对象隔离、fixed基准、locks和structure；同一owner、同一完整head的数值结果可复用，但每次仍新事务全量scan全部raw/hash/metadata，复核完整语义身份及缓存receipt digest。新增terminal head与fresh owner重新完整数值审计。统一snapshot对检查、读取、缓存写入及连接关闭异常均清缓存并poison；原异常保留。阈值、v2科学规则、232-stage顺序、3600s task和2440s overhead预算均保持。

独立PRE_SEAL reviewer /root/h1_perf_preseal静态findings已闭合。稳定版本7文件205 passed in347.70s、exit0；随后只修复最外层precheck异常覆盖并新增反例，正在重跑受影响archive/collector/Job/gate四文件。最终DRAFT request SHA256=b573084c40c46774e13a3f14148ac903d3ab3d1dec4f30a9b5278e856f594f3a，位于review_candidate_complete_non_authoritative目录；完整232 saved-worker计时仍待完成。旧895 sealed成员和248 run文件复核零漂移。未封存v3、无official verdict、新native未授权且未启动；正式研究资源、共同Rref/A及完整支持LB/UB继续开放。

## 2026-10-02 H1 v3 完整 worker 收尾成功但性能门未通过

完整保存数据worker已完成232阶段、child accepted_terminal（233 events）、registry attempt_outcome（235 events）、236条anchor和fresh reopen，最终程序因固定non_solver_seconds=2440性能门拒绝而退出1。无新的native调用；mocked capture的summary计数232不代表native solver调用。该轮脚本未输出精确elapsed，不补造精确时长；worker_result SHA256=22c2f0e764c219f94777061cef5ea5ba2d29c5f1baa04e83b0dc78746fc6b370。失败观察及245文件inventory为saved_worker_budget_rejection.json（SHA256=3f6c2a92ba30a04c13233c29b3ba2f992ac4e6738d9b9dc64125876288a69acd），改前v3源码/test/spec已保存到pre_anchor_source_snapshot_non_authoritative。

尚未封存v3。正在增加独立full_attempt_anchor_v3：同一次完整scan以一次稳定读取同时校验retained identity/hash和chain；每次inspect/confirm仍full scan，advance前后检查、fsync及读回保持。旧236-record anchor单次profile为474次read、0.72426s，主要位于路径/文件identity检查；该profile带测量开销，不外推正式运行充分性。新anchor容量和失败窗口测试、独立PRE_SEAL、完整2440s保存数据性能门仍待。后续脚本将在性能门判定前保留精确measurement。旧冻结产物不改，新native未授权且未启动，正式研究资源/Rref/A/完整支持LB/UB仍开放。
## 2026-10-02 H1 v3 完整性能门通过，封存机械修复

最终 anchor_saved_worker_non_authoritative 已完成 232-stage、terminal/outcome 和 fresh reopen；2264.4797890000045s < 固定 overhead 2440s，余量 175.52021099999547s。逐次 1392 项 stage audit 比较通过，raw 顺序、numeric pin、lock hex、mapping 和完整 projection payload 与保留的 v2 oracle 一致。diagnostic SHA256=9ea373b9d34e469be6b96d9153771981865d228a7e1dc233ecfbace187341451。当前源码绑定测试：anchor 34 passed、v3 integration 159 passed，退出均 0；证据 anchor_development_test_results.json SHA256=dae424c4ee2325036cea3836000bf8aa240c1884dfb7677d8364c29c72153d7b。旧 895 个 sealed 成员和旧 run 248 文件均保持。

/root/h1_perf_preseal 独立 PRE_SEAL findings 已闭合。首次机械封存在写 inner 前被普通 Job 记录 256KiB 上限拒绝；只留下 config/lease，未到 outer commitment，未 consume/native。原脚本、证据和两叶完整保留，mechanical_seal_failure.json 记录失败；独立 recovery 脚本按清单 reader 原有 2MiB 上限预检大小、核验两叶独立 pin 后完成排他写入，不改变 runner、资源预算或科学规则。机械修复仍须预审后封存，再由全新 reviewer 审查 exact outer。

本轮为零 solver 保存数据开发验证，未测 native capture 开销及完整 Windows Job 监督，不证明 whole-task 资源充足。新 native 未授权且未启动；正式研究资源准入、共同 Rref/A 和完整支持 LB/UB 仍待完成，formal_execution_ready/formal_result 继续 false。
## 2026-10-02 H1 v3 seal commitment 完成

机械 recovery 在独立 PRE_SEAL 闭合后执行，退出 0。config/lease 原字节保持，inner/outer 使用既有 manifest 2MiB 上限完成排他写入、fsync/readback；pending 完整验证后原子 rename，canonical outer 再次验证通过。exact outer：configs/rq2_normal_h1_calibration_v3.OUTER.SHA256SUMS.json，SHA256=e3acc7a6de1c1863ab64a8c1ae67ded9676e01c564a3d4ef2d0be29252f0edcf，共1695成员。PRE_SEAL证据 development_checks_recovery.json SHA256=4297ce0e3a910067b97bba7ea72dac9ad50d182d6bc5e31ce407a9dc54109af7。

全新只读 /root/h1_performance_v3_official 已开始对 exact outer 作 official review。当前尚无 official verdict；native authority/consume/root 均未创建。sealed 实现与证据不可再改。完整研究资源/Rref/A/完整支持LB/UB仍开放，formal_execution_ready/formal_result=false。
## 2026-10-02 H1 v3 official PASS；等待新的单次 native 授权

全新独立只读 /root/h1_performance_v3_official 对 exact outer e3acc7a6de1c1863ab64a8c1ae67ded9676e01c564a3d4ef2d0be29252f0edcf 给出 official PASS，无开放 finding，冻结验收矩阵1–7满足。独立回归159 passed in333.98s/exit0；anchor故障窗口33 passed、1 deselected in5.13s/exit0，完整385-record容量循环已有封存开发证据。测试后1695成员零漂移、verify_package通过；旧895成员/248运行文件全保持。根记录 results/tables/rq2_normal_h1_full_job_v3_non_authoritative/calibration_v3.official_review.json，SHA256=cc5d7f3196df898f58356463cc6538cf5787aef135bd0e7392caed4faff9660c；详细审查证据 calibration_v3.official_review_evidence.json，SHA256=208562b4880a2e0484c3e4043d01f575d10f5ca46934c683d5a1436e82315f92。

review gate已关闭，native运行权限门仍未打开：旧v2一次性claim已消费；本次请求新v3一次训练单小时232-stage native calibration，固定单线程、5s/stage、3600s task、2GiB Job、不自动重试。尚未创建v3 authority/consume/native root，未启动。须用户对该具体新动作明确授权后才能进入预检查和执行。完整研究资源准入、共同Rref/A和完整支持LB/UB仍开放，正式研究实验尚未开始；formal_execution_ready/formal_result=false。
## 2026-10-02 H1 v3 用户授权并启动单次 native 校准

用户对上一条具体 v3 单次运行请求回复“确认”。根核验 exact outer e3acc7a6de1c1863ab64a8c1ae67ded9676e01c564a3d4ef2d0be29252f0edcf、official PASS 和无活动相关进程后，登记 calibration_v3.user_authority.json SHA256=0498995a241b687f606ea8a0674918df83ea6904096b15124d34804d0b373294；execution_gate SHA256=6ec6b6bd95212bf9f044518ebcabf9c830c62106c23c851f2341a64e8fc25137。prelaunch_headroom SHA256=228b7dbd626a412d9be734eb584344b4237232e132d32bc71865c5271bc756b7，observed_headroom_sufficient=true、errors=[]，仅为启动前快照。

公共 run_job 已消费一次性 claim 并启动新的 Windows Job，controller PID33484、worker PID35044，根为 results/tables/rq2_normal_h1_origin_calibration_v3_non_authoritative。固定232 stages、5s/stage、单线程、3600s task（含2s quiet）、2GiB Job；不自动重试。当前运行中，尚无终态，不记为成功。该动作仅为单小时校准；完整研究资源/Rref/A/完整支持LB/UB仍开放，正式研究实验尚未启动，formal_execution_ready/formal_result=false。
## H1 v3 单次 native 完整结束，待独立 post-run 复核

已授权的一次v3 native校准正常结束，controller与worker均exit0；process_observation reason=child_exited、elapsed=2744.9839999999967s、whole_job_quiescent=true、last_resource_errors=[]。Job commit limits已配置，peak process268324864 bytes、peak total Job269524992 bytes。worker保存232份报告并返回accepted，fresh_reopen_equal=true、solver_calls_by_replay=0；worker_result和job_checks均存在且绑定通过。原PID33484/35044已退出，无自动重试。

运行根 results/tables/rq2_normal_h1_origin_calibration_v3_non_authoritative 保留251files/20938085bytes；postrun_inventory SHA256=e80dacf5c44b39ad71ff29dce980d3e03cee6f4bf9fad6d3be620061e171d596，run_observation SHA256=29b1b997cb15623bfe956c6d37b6e112974323a8c168506692001a0fdd958edd，均在 results/tables/rq2_normal_h1_full_job_v3_non_authoritative。根SQLite完整性检查通过：child233 events、registry235 events；anchor236 records。sealed package/consumed gate复核通过，旧v2 run248files保持。独立只读 /root/h1_performance_v3_official 正作post-run evidence audit，不是新official verdict。

此次证明单小时校准在总task/Job限额内完成；2744.984s整体wall不单独证明2440s non-solver分项预算充足，native capture开销未单独计时。机器记录whole_task_resources_verified/formal_execution_ready/formal_result/native_execution_authenticated仍false。完整研究资源准入、共同Rref/A、完整支持LB/UB继续开放；不启动后续实验，不重复使用已消费claim。
## H1 v3 单次 native post-run 独立复核闭合

/root/h1_performance_v3_official 完成有界只读post-run evidence audit：证据充分、无阻断finding；不是新的official verdict，不授予后续运行。calibration_v3.postrun_review.json SHA256=51519252f9d570a45625cabf9b2f9e20e5701f530608b9e599d4ccafa0144ff4，位于 results/tables/rq2_normal_h1_full_job_v3_non_authoritative。

独立重算registry235/child233 events、232 chunks、233 checkpoints、236 anchor全链闭合，无孤儿数据；232 stages的index/objective/stage_identity/numeric SHA/locks/prior-locks/generation mapping与saved-worker均无差异，terminal完全一致，payload SHA256=034d14eb5728732790177a2f76af7fa552d9a7dad56ecfbfaf43d217eb7b2cc9。203份raw含不同attempt运行字段，各自原始链均完整，不要求跨attempt raw字节相同。唯一normalization仍是获批stage25的小负generation转零，candidate errors=[]。新1695 sealed成员、251运行文件、旧895成员和旧248运行文件均零漂移。worker和job_checks完整绑定，fresh reopen一致。

单小时native校准已完成：2744.984s、controller/worker exit0、Job quiescent；原v2超时结果保持不变。本次成功只关闭该校准执行与post-run完整性检查，2440s non-solver分项仍未独立证明；完整研究资源准入、共同Rref/A、完整支持LB/UB继续开放，formal_execution_ready/formal_result/whole_task_resources_verified/native_execution_authenticated均false。一次授权已使用，不自动重试或启动后续实验。
## 2026-10-03 v2完整支持资源目录与后继设计开发

用户要求“继续做吧”。本轮新增零solver资源审计 experiments/audit_rq2_h1_resource_readiness_v1.py，独立pin已批准v2配置95eb158f0a8e6784d2af401e67164965543c98f42ff02b756c214982601e5430、既有完整coverage29ba7f5662c3dee019f183104479d8fa354f726bea0e055ee456b3dd337042c4及v3封存/运行/复核证据。由1091条边际窗口重算training14644/holdout14336，保留604/593缺尾pair；19theta×100alpha=1900cell，不沿用旧46cell提案。

可索引因子目录覆盖training27,823,600 cell-pair、111,294,400四臂对象；潜在D网格LB/UB义务22,481,468,800，不是必须执行的solver任务；holdout108,953,600条件评价身份不乘D网格且未冻结UB保持null。真实causal keys、可执行task manifest和全研究资源总量仍null，复用边与解析排除证明均空，不作资源折扣。

审计产物 results/tables/rq2_h1_resource_readiness_v1_non_authoritative/resource_gap_audit.json SHA256=d8110cdf8d448cef78f1cb9432125521bf917d84896ebb99ada862e243b73f02。当前一条192h normal内容cap774088294400bytes大于卷快照free110590214144bytes，差额663498080256bytes，尚未加额外overhead/scratch/reserve；这只拒绝当前cap全预留方案，不证明最低实际存储量或完整研究不可行。单小时Job2744.984s不证明2440s non-solver分项，相关字段保留null。

23项定向测试通过（0.40s、exit0），审计CLI exit0；新设计 docs/model_spec/rq2_h1_resource_successor_design_v1.md 规定专用序列化上界证明、分段monotonic timing、完整parent、合法复用DAG、Rref/A和容量证明任务的后继验收。现阶段只完成目录、条件算术和设计，没有实现这些后继组件或创建新run authority。独立只读开发审查进行中。v3 1695封存成员/251运行文件及旧v2 248运行文件复核保持，未修改src、未启动native，正式研究门仍开放。
## 2026-10-03 资源义务目录开发审查闭合（纠正前段初版计数）

独立只读 /root/h1_performance_v3_official 开发审查无开放finding，非official verdict且不授予运行。初版把offline LB也乘101个D，并漏可索引B6 shared actual；两项均已修复，D=0/1端点保护与不兼容schema版本问题也已修复。前段22,481,468,800统一LB/UB计数已失效，仅保留为开发历史。当前四family为：training LB111,294,400（无D），training UB11,240,734,400（101D），training B6 actual27,823,600（无D、条件评价），holdout108,953,600（无D/proof）。所有eligible counts、frozen UB、solver task及证书仍null，不构成实际调度清单。

最终 results/tables/rq2_h1_resource_readiness_v1_non_authoritative/resource_gap_audit_v2_final.json SHA256=1a31bdd0d69b717525e1d281f4d53d21bf8f8cca929732b76847cfa332843ad1，外层schema=h1_resource_readiness_gap_audit_v2、目录schema=factorized_capacity_obligation_catalog_v2；开发检查 development_checks.json 绑定最终代码/test/spec与全部历史。根27passed in0.42s/exit0，独立27passed in0.41s/exit0；只读重算除磁盘瞬时值与时间戳外完全相同。原始及中间产物和两轮代码快照完整保留。当前卷free110588981248bytes，192h单条normal的774088294400bytes内容cap仍超出该快照；这是cap预留方案差额，不是最低实际磁盘需求或科学不可行证书。

本轮关闭固定证据/支持量、可索引潜在义务目录、normal-only条件算术及后继设计的开发检查。专用序列化cap证明、分段timing、192h parent、实际causal reuse DAG、Rref/A、LB/UB算法、可执行任务manifest和完整资源pilot/准入仍待；未启动native或formal run，无新lease/authority/official receipt。全部formal/whole-resource ready标志保持false。
## 2026-10-03 H1 条件存档界与计时原语开发

用户要求继续推进。根唯一写入新增 experiments/h1_report_byte_bound_development_v1.py、experiments/h1_segment_timing_development_v1.py、对应两份 tests 与 docs/model_spec/rq2_h1_resource_primitives_development_v1.md，未改 v3 sealed source closure 或 native runner。

存档语法在每通道最多362 objective terms、891 assignments、UID完整JSON token最多38字节、有限字段语法的条件下，compact serializer组合上界为929218 bytes；将term上限设为891时为2093021 bytes。整数算术覆盖Fraction聚合/乘积/差，拒绝额外key、错误类型、超长及超量。v3全部232原始raw逐项hash/length/canonical bytes验证通过，最大实测177312 bytes，原字节不变。362及UID条件尚待对所有未来模型和native导出证明，producer_coverage_proven=false；不把该条件界登记为已生效1MiB cap。旧16MiB采集、异常/oversize持久化路径保持。

计时原语实现逐span open/complete/unknown、单PID/thread/domain、嵌套exclusive合计、未分类余量、clock/usage/exception poison及bounded exclusive snapshot写入。recorded_window_wall_ns仅为记录窗口；最终snapshot写入有单独observer interval，snapshot构造和receipt后续开销未全部归属。它仍是内存ledger，未接完整worker、未实现crash-durable start；instrumentation/component-budget标志为false，不能证明2440s分项预算。

根合并验证77 passed in2.04s/exit0；独立只读复跑77 passed in2.20s/exit0。旧v2 outer895成员及run248文件、v3 outer1695成员及run251文件均零漂移，git diff --check通过，无相关Python/Gurobi进程。当前机器证据 results/tables/rq2_h1_resource_primitives_v1_non_authoritative/primitive_audit_v2_final.json SHA256=3d37dc951f586055fff5dc6a1e0e8803851d22797a6840612b97e39e2111ce29；初版artifact保留，最终补显式resource_admission=false和source/test/spec哈希绑定。独立开发审查闭合记录以同目录development_checks.json为准，非official verdict或运行许可。

本轮没有新native调用、封存包、lease或authority。完整producer覆盖证明、collector持久化失败通道、worker timing接入、192h parent、实际reuse DAG、Rref/A、完整支持LB/UB及完整资源准入仍待；全部正式执行/结果/完整资源标志继续false。
## 2026-10-03 H1 future shape 与 raw-before-audit 入口开发

本轮发现并复现旧单小时1211约束上限不覆盖future carry：固定pinned RTS loader族下，core954 + reserve26 + residual dwell最多61 + strict locks最多231 = 1272。新增零solver脚本枚举891变量名及362项成本系数，逐项与canonical模型一致；后231目标为单变量，UID JSON token上限38保持。192个来源行的thermal bounds和reserve area keys已核对。合成relative_hour=1 carry及合成locks得到1272约束，但reachable_assignment_proven/scientific_witness=false；这是接口规模反例，不是可行调度或已发生的未来轨迹。任意hourly bounds族需1465，允许generic age0需1477，不能混用为1272。

新增 experiments/h1_producer_shape_development_v1.py、h1_report_byte_bound_development_v2.py；v2仅开发grammar将constraints改为1272，字节界仍929218。旧v1 grammar、v3的1211和16MiB合同均保留。proof现显式verify既有v3 exact outer e3acc7a6de1c1863ab64a8c1ae67ded9676e01c564a3d4ef2d0be29252f0edcf/1695成员，并直接pin residual dwell和job binding模块，关闭首轮遗漏依赖问题。producer/native export总覆盖标志仍false，真实successor尚未绑定完整逐hour source入口或native terms guard。

新增 experiments/h1_raw_ingress_development_v1.py：create-once单owner，intent→原raw完整写入/fsync/fresh readback→receipt→consumer→outcome；异常poison、external abort、无retry/repair。reader改为同handle cap+1有界读取、前后文件身份及最终完整视图复核，修复独立审查发现的stat/read增长窗口。232份保存raw经新tmp磁盘入口逐字节保留；既有3stage collector的saved-capture测试接缝证明科学audit前raw/receipt已存在，audit异常后raw保留且入口拒绝继续。只在test使用gate替身及saved provider，solver被显式禁止；未生产接线。fsync不升格为断电目录项/卷级保证；额外raw副本与metadata仍需完整资源预算。

修复闭包前合并113 passed in40.83s/exit0；闭包修订后受影响5项tests passed in7.56s/exit0。独立审查终态以 results/tables/rq2_h1_producer_ingress_v1_non_authoritative/development_checks.json 为准。当前 producer_shape_audit_v2_final.json SHA256=9670a3cae30b40a9963aba73e757b25a27635598b9e6bed89c4fc489b076fd49；初版e073f1b9f2559b6c6659d297e3723ced48be0610500c72c5661843b8a06f1bf4及七文件snapshot保留。细节见 docs/model_spec/rq2_h1_producer_ingress_development_v1.md。

旧v2/v3封存895/1695成员及run248/251文件无漂移，上一轮development evidence pins无漂移，git diff --check通过。正式实验仍未启动；本轮native调用0，无新封存包/lease/authority。后续须完整source parent、native guard、collector/timing生产接线、fail-stop存储分类与资源预算、Rref/A、完整支持LB/UB和完整准入；formal_execution_ready/resource_admission/producer_coverage_proven均false。
## 2026-10-04 H1 saved-source parent 与 native export guard 开发审查闭合

根唯一写入，新增 experiments/h1_saved_source_parent_development_v1.py、experiments/h1_native_export_guard_development_v1.py、对应两份 tests/spec。saved parent 按固定 origin 推进双 raw index，逐 hour 绑定 source/chain/package/clock 与前驱 carry；先锚定 intent，再消费 saved reports，child fresh reopen 和父前缀重验后写 outcome；异常 poison，无 retry，reopen 只读。没有独立 hour Job/native 入口；missing-tail 仅 pre-intent fail-closed，无 typed censor 终态；raw ingress 和完整 timing 未接。

192h 合成状态机容量单项通过：384父events、385anchor、192完成/attempted小时及fresh reopen。child采用明确test-only oracle，每小时3stages、共576合成槽位，不是RTS future producer/native witness。另用真实 pinned RTS 静态网络验证232×192=44544槽位的初始声明、0attempt/events、385anchor容量；不是192h执行或资源准入。调用计数为solver_calls_by_parent=0、历史source_solver_calls=None。

native guard检查live retained handles全集/正反映射、native ModelSense精确int1及canonical/native Fraction algebra；saved guard检查v2 grammar、变量全集、referenced assignment和objective terms/algebra/exact值。保存v3 origin的232份raw逐阶段actual model检查通过。fake live handles未证明adapter实际wrapper身份；saved raw不证明live reverse map或future carry。返回仅表示shape/objective对应，完整科学replay仍必需。ingress后的超界/错配guard拒绝测试保留完整raw并禁止retry；尚未生产接线。

根初轮parent16 passed/145.58s。扩展批1 failed、20 passed/1137.00s、exit1：唯一失败是test-only restore注入器在检查poison时再次抛模拟异常，192h单项本身通过。修正fixture及调用计数字段后，最终受影响20 passed/114.18s、exit0；另加RTS声明1 passed/6.16s、exit0。容量被测三文件snapshot保留；snapshot到最终parent实现只有Inspection调用计数字段改名及新增None，独立审查确认状态机/容量无变；不得把原失败整批记成通过。相关source/anchor/shape回归70 passed、1 deselected/10.70s、exit0。guard修复native sense遗漏后30 passed/52.11s；新增超界保留反例4 passed/6.74s，均exit0。

独立只读 /root/h1_parent_review 开发审查无开放finding；独立guard完整33 passed/53.31s、parent关键子集10 passed、12 deselected/93.43s，均exit0；git diff --check通过。非official verdict，不授予运行。机器记录：results/tables/rq2_h1_saved_source_parent_v1_non_authoritative/development_checks.json；测试历史、失败分类、容量snapshot单独保留。旧封存895/1695成员、运行248/251文件及上一轮开发pins核验无漂移。

仍待：独立hour Job/完整worker，raw ingress/guard/timing生产接线，typed missing-tail、失败storage分类及新增副本资源预算，实际合法reuse DAG，共同Rref/A，完整支持LB/UB及全任务manifest，完整准入/封存/全新official审查。新native须针对具体就绪包另行明确授权。producer_coverage_proven/native_export_coverage/collector_integrated/resource_admission/formal_execution_ready/formal_result均false；本轮新native调用0，无新lease/authority/production outer。

最终开发检查 SHA256：b2874c1d29577ebc7360416b3113702c41303ab03733fe72fcf701a4bd54afe3。补充区分：v2旧895成员/248运行文件字节保持，但其动态all-src verify_package在当前checkout返回complete local source closure required；缺口恰为10个早已封存于v3的源文件，非本轮新增或漂移。v3 exact verify_package通过。旧v2执行门不能在此checkout据此复用，不修改旧gate；这不改变本轮零native或全部正式门关闭的状态。

### 2026-10-04 H1 durable guarded ingress development v1

新增 experiments/h1_durable_timing_development_v1.py、experiments/h1_guarded_ingress_development_v1.py 及对应 tests/spec。持久 begin/end journal 支持重复 phase、嵌套 exclusive、单 owner、create-once、4096 spans/8193 events、每文件2048 bytes；begin写盘/fsync/fresh确认后才执行body。缺尾/部分写/时钟倒退/未知terminal pin均unknown、总量None，poison不重试。成功receipt带request/binding/terminal pins，完整计量依赖外部独立保留pin。真实子进程os._exit(17)覆盖begin后中断；不声称目录项断电持久或hostile ABA防御。

SavedStages固定guard及完整开发依赖pins，顺序raw完整保存→receipt→guard→scientific consumer→outcome。SavedHour从真实packet/spec/limits构建stage模型，执行v3 _audit_stage，audit前后核验request/实现，outcome后才推进lock；完整finish要求全部保存raw fresh replay_stream。真实RTS origin原raw前2stage科学复核通过。完整finish另用明确test-only synthetic三stage fixture：复制旧tiny raw，仅TimeLimit元数据1→5，源SHA/原文件不变、新SHA不同；真实guard/audit/replay代码执行。该fixture不构成5秒native采集或scientific/native witness，不提升RTS整小时或producer coverage。

根合并回归88 passed/80.04s/exit0；末次post-audit身份漂移修复后guarded整批15 passed/38.09s/exit0。独立只读 /root/h1_parent_review 初整批30 passed/37.02s/exit0（末次修复前），修复单项1 passed、14 deselected/14.81s/exit0；三项finding全部闭合。非official verdict，不授予运行。git diff --check通过。v2/v3封存895/1695成员、运行248/251文件及上轮15 pins无漂移；旧v2动态all-src closure限制继续保留。

单adapter规定内部路径232stage逻辑上界3896610816 bytes、2330 files、235 directories。保留16MiB raw cap，不用929218条件界替代保存预算；不含旧SQLite、parent/Job产物、任意callback额外写入或filesystem allocation，不能据此准入。guard_execution_durably_attested=false：raw outcome未绑定guard receipt/adapter terminal。observer开销未独立分离，terminal tick后I/O不在recorded window，2440秒分项仍未证。完整232stage新入口finish未验证，尚未接独立hour Job/生产collector。

开发检查：results/tables/rq2_h1_durable_guarded_ingress_v1_non_authoritative/development_checks.json，SHA256 c506cce23c9202b31e00561dbaed0af5019e305029d5715f8c22a6b233d91d96。同目录保留test_results、independent_development_review、preservation。producer_coverage_proven/native_export_coverage/collector_integrated/resource_admission/formal_execution_ready/formal_result均false；本轮新native调用0，无新production outer/lease/authority。

仍待持久guard/scientific attestation、完整worker与独立hour Job、逐hour source/carry及typed missing-tail、全分段与observer计量、失败storage分类和整任务副本预算、实际reuse DAG/task manifest、共同Rref/A及完整支持LB/UB、完整准入/封存/全新official审查。新native须待具体包和门禁就绪后另行明确授权。

### 2026-10-04 H1 attested saved hour development v1

新增 experiments/h1_attested_saved_hour_development_v1.py、对应tests及docs/model_spec/rq2_h1_attested_saved_hour_development_v1.md，保留全部旧绑定字节。saved-only小时binding固定科学request、packet.audit_identity（含来源时钟）、开发/科学实现、adapter/raw/timing bindings。因果计算key不变，额外audit pin拒绝inputs相同但sourceclock不同的packet。

持久顺序为raw/receipt→固定guard/guard receipt→v3科学audit→完整generation mapping→science summary→raw outcome/capture timing end→stage commit；commit fresh确认及postcheck后才推进lock。失败poison且保留部分文件、不重试/恢复。科学拒绝若附mapping也先按cap保存再停止。mapping保留原值/新值/差值、raw/candidate audit，science hash与reader完整重算共同绑定，不只保存摘要。

full finish先全部保存raw fresh replay_stream，再raw/timing terminal，随后projection和hour terminal；hour terminal绑定最后commit、projection及report/stage/numeric向量、raw/timing终态。独立reader要求外部保留binding/terminal pins，重建每stage guard/audit并完整replay_stream，核对精确timing事件及所有文件完整fresh view。该链证明saved-data复核闭合，不认证历史native或live reverse map。完整RTS 232stage finish尚未验证，也未生产collector/Job接线。

真实RTS原raw前2stage前缀通过。完整成功/失败路径使用明确test-only synthetic三stage fixture，旧tiny样本仅TimeLimit元数据1→5，源bytes/SHA保留；不构成新native/scientific witness。另直接验证既有v3 stage25已审negative mapping原样存档：1838 bytes，SHA256 2f508ce4d138317d049cc08ec7e6e705b16890237f139929d7dab925e30bad13；原raw SHA256 0bbffb4cb0ceb39354854ad7bbde60cdda62ecbf94ce74577091455021701588，唯一201_CT_2 negative→0及delta完整保留。此项为storage-only，不重做0..25 prefix或科学规则。

测试历史分列保存：初27 passed/58.98s；扩展合并71 passed/120.98s（完整mapping增加前）；reader末端clock检查2 passed、39 deselected/11.38s。mapping扩展批1 failed、45 passed/155.92s/exit1，唯一失败为test将JSON list与内存tuple比较；改为canonical bytes比较后affected3 passed、44 deselected/9.85s/exit0。独立审查先前41项因根并发修改draft而失效，1 failed、40 passed/139.47s/exit1，记录INVALIDATED_BY_CONCURRENT_DRAFT_EDITS，不作稳定实现通过或失败判定。最终静止快照独立 /root/h1_parent_review 单文件47 passed/158.00s/exit0，无开放finding；非official verdict。git diff --check通过。旧895/1695封存成员、248/251运行文件及上轮15pins核验无漂移；旧v2动态all-src closure限制不变。

新增每stage三个2048-byte metadata及一个256KiB mapping上限，另计binding/terminal/projection。232stage单入口内部路径逻辑上界3959119872 bytes、3261 files、236 directories；不含外层parent、旧SQLite/Job日志、allocation及目录开销，不能升级资源准入。guard/mapping/science I/O在audit span，raw outcome在capture；stage commit/postcheck在recorded window内未分类，最终projection/attestation terminal/reader在window外。observer未分离，2440秒分项仍未证明。

开发检查：results/tables/rq2_h1_attested_saved_hour_v1_non_authoritative/development_checks.json，SHA256 cf873d74425b36e9d59f1bcb80b3f8d5245010f9bc1eb68bc839bb08f4f1279d。该目录保留preservation、test_results、invalidated_independent_run、independent_development_review。producer_coverage_proven/native_export_coverage/collector_integrated/resource_admission/formal_execution_ready/formal_result均false；新native调用0，无新production outer/lease/authority。

整体目标继续进行：尚需完整worker/独立hour Job、逐hour source/carry和typed missing-tail、全分段/observer计量、失败storage分类/整任务预算、实际reuse DAG/task manifest、共同Rref/A和完整支持LB/UB、完整准入/封存/全新official审查。具体新native运行仍须就绪包与门禁完成后另行明确授权。

### 2026-10-04 H1 attested source parent development v1

新增 experiments/h1_attested_source_parent_development_v1.py、对应tests及docs/model_spec/rq2_h1_attested_source_parent_development_v1.md。继承已审saved parent的逐小时source/carry/journal/anchor状态机，以新declaration identity接入持久guard/scientific attested child。wrapper绑定parent intent、source lineage、科学request、packet audit、core binding/terminal和owned replay projection；完整fresh reader及typed projection通过后才允许parent outcome/carry推进。既有源码、封存与结果字节保留。

两个小时、每小时3stage的显式synthetic fixture已通过来源/时钟/连续carry、4个parent events/5个编号anchors、fresh reopen；hour1根据真实before carry构造transition bits，再经真实guard/audit/replay，原raw不改。错误来源、hour0 raw用于hour1、跨小时terminal替换均拒绝。此项不是native capture或RTS可达性/192×232 producer覆盖；192小时容量仍仅引用旧基类test-only child oracle证据。

失败测试覆盖child未完成、wrapper terminal写前/确认后/reader失败、parent outcome前失败、outcome journal已写但anchor未推进，以及typed projection重放期间core变化。保留部分归档、停止，不补做outcome/重试/恢复。最后一类anchor失败重开由independent chunk head校验拒绝；未把unknown解释为数学不可行。

根14项整批248.25s/exit0；新增两个失败窗口初1 failed+1 passed/33.64s，失败仅为断言预期错误文本与实际更早fail-closed检查不一致；修正后定向1 passed/15 deselected/20.19s/exit0。最终静止快照独立只读 /root/h1_parent_review 16 passed/279.07s/exit0，无开放finding，非official verdict。完整早期fixture错误和修复历史保存在test_history.json。git diff --check通过。v2/v3封存895/1695成员、运行248/251文件及前序saved-hour16pins、saved-parent15pins无漂移。

232stage每child逻辑上界3959123968 bytes、3263 files、237 directories；未计parent/Job/filesystem allocation。core与wrapper为完整独立读与typed projection存在重复科学重放，parent历史restore累计O(hours²)，不能沿用旧v3 wall或2440秒non-solver预算进行资源准入。

开发检查：results/tables/rq2_h1_attested_source_parent_v1_non_authoritative/development_checks.json，SHA256 122e4928cade82c7165fdbe2c46e36bf4f7a01ddaa20a1d2f901c02e1e25f498。43个文件pins包含前序开发依赖、10个测试fixture传递依赖、sample archive及本轮审查/测试/保存性证据。所有producer/native_export/collector/independent_hour_jobs/resource/formal_execution_ready/formal_result门均false；新native调用0，无新production outer/lease/authority。

下一步为完整worker与独立hour Job、typed missing-tail、完整分段/observer、失败storage分类与全任务资源预算；仍需实际reuse DAG/task manifest、共同Rref/A及完整支持LB/UB、完整准入/封存/全新official独立审查。具体新native运行须在包和门禁就绪后另行明确授权。整体目标继续进行。

### 2026-10-04 H1 child storage classes development v1

新增experiments/h1_child_storage_classes_development_v1.py、对应tests及docs/model_spec/rq2_h1_child_storage_classes_development_v1.md，为后继独立hour Job预算补齐固定saved parent路径的成功／首次失败存储分类。保持所有原代码与原16MiB上界不变。

成功stage经canonical grammar guard限制raw≤929218 bytes；raw-before-guard允许首次失败raw完整或部分保存至16MiB。固定parent逐层poison、create-once、重开仅检查，因此整个H小时路径至多一个raw未成功经过guard，未来小时不创建。此条件排除直接调用内部owner/abort、任意callback、外部写入及重试。每child完整nonraw槽位继续保守计入：C=(12S+14)×2048+(S+1)×262144。完整成功界H×C+HS×929218；首次失败停止界H×C+(HS−1)×929218+16777216。

H=192、S=232时，成功内容54218578944 bytes；包含首次失败的保留内容54234426942 bytes；文件626496、目录45504。原全raw-cap界760151801856 bytes继续保留。可显式给allocation quantum逐文件round，但只给条件file-content界，不含filesystem metadata、parent SQLite/anchor、Job/scratch、上游raw副本或其他写入；不是磁盘准入。O(H²) replay计时与全任务预算仍未证明。

根最终20 passed/15.02s/exit0；独立只读 /root/h1_parent_review 20 passed/15.73s/exit0，无开放finding，非official verdict。测试独立枚举首次失败位置，覆盖H/S端点、B+1和16MiB raw（首stage或成功前缀后）、部分写入保留、poison后无新增文件，以及完整synthetic child逐文件cap；新native调用0。git diff --check通过。v2/v3895/1695封存成员、248/251运行文件和前序43pins无漂移。

开发检查：results/tables/rq2_h1_child_storage_classes_v1_non_authoritative/development_checks.json，SHA256 6168eb58d57d6292ef909dc20eeed0356b3994fece89dd8f482e70292289a425，绑定51文件pins。条件child内容界已完成开发审查；parent/Job/filesystem及完整resource admission仍false，producer/native_export/collector/formal_execution_ready/formal_result仍false。无新production outer/lease/authority。下一步继续完整worker与独立hour Job、全计时/observer、完整资源与任务manifest/reuse DAG、共同Rref/A和LB/UB；正式运行须完整门禁及新的具体授权。

### 2026-10-04 H1 bounded file parent development v1

新增experiments/h1_file_parent_journal_development_v1.py、experiments/h1_bounded_file_parent_development_v1.py、对应2tests及docs/model_spec/rq2_h1_bounded_file_parent_development_v1.md。旧parent的SQLite内容预算不覆盖index/rollback空间；后继parent实际接入有界不可变事件文件，旧SQLite实现/封存/结果保持原字节。metadata.bin和payload.bin各≤256KiB，commit.json≤2048bytes；xb/fsync/fresh read后完整prefix核验，最后推进live head；原anchor独立保留head。最多384events，部分/完整但未锚定tail、gap、额外文件、live替换均拒绝，无截断/修复/恢复。

parent来源/clock/carry/typed child/anchor语义保留；_restore仅把私有SQL head查询换成event_head接口，以AST等价测试核对。构造器增加独立root lease并接入新journal；新declaration阻止旧协议误开。root、journal、anchor分别计入预算。close修复了重入拒绝后误释放root、inner关闭失败及root已释放后确认异常的窗口：parent guard先行；inner成功后detach；root最后先detach再close，旧对象不能影响新owner。失败后只允许完成teardown，不允许继续实验。

测试按快照分列：根初短16 passed/2 deselected/11.95s；初完整19 passed/552.25s/exit0，实际384event写入及385拒绝、两小时synthetic carry和fresh reopen通过。独立22 passed/1 deselected/153.50s是close窗口修复前快照；根后续21 passed/2 deselected/13.20s、中间close根7 passed/1 deselected/12.50s及独立7 passed/1 deselected/12.43s分列保留。最终root close定向根5 passed/4 deselected/8.74s，独立 /root/h1_parent_review 5 passed/4 deselected/8.82s/exit0，最终无开放finding，非official verdict。journal实现及容量测试AST与初完整快照相同；parent source/carry等函数AST未变。没有声称最终27项在同一次命令中全部运行。

H=192/S=232的条件parent+child文件内容界54461838913 bytes、628038 files、45891 directories；包含全部child、parent events/header/locks、anchor header/385records/lock及root lock。尚未含Job/scratch/上游raw副本/FS metadata和allocation。科学重放累计O(H²)；逐event全prefix扫描在反复restore中可累计O(H³)文件工作量，时间准入和2440秒分项未证。

开发检查：results/tables/rq2_h1_bounded_file_parent_v1_non_authoritative/development_checks.json，SHA256 5f7a70ee1ee0d97216c4a63f6c2cfb04081d1b6ac7c533aa044c72861b76cbc8，绑定68文件pins；初完整snapshot和全部后续测试/审查历史保留。git diff --check通过；旧v2/v3的895/1695封存成员、248/251运行文件和前序51pins无漂移。新native调用0，无新production outer/lease/authority；producer/native_export/collector/independent_hour_jobs/resource/formal_execution_ready/formal_result均false。

继续完整worker与独立hour Job、typed missing-tail、Job/FS/完整任务资源及observer/时间门禁、实际reuse DAG/full task manifest、共同Rref/A和完整LB/UB，随后封存及全新official独立审查。具体新native运行仍须就绪包与门禁完成后另行明确授权。整体目标保持进行中。

### 2026-10-04 H1 parent snapshot worker-input development v1

新增experiments/h1_parent_snapshot_development_v1.py、对应tests及docs/model_spec/rq2_h1_parent_snapshot_development_v1.md。只读snapshot允许parent保留writer root/journal/anchor lease时，由另一进程核验外部pin下的完整前缀并重建当前source/carry；不注册、获取或释放writer锁，不读msvcrt锁住的首字节。Journal/Anchor Snapshot复用已审扫描器，写接口硬拒绝；network由pinned origin加载，future before仅由已保存完整child科学replay得到，不反序列化owned carry。

只接受events=2h+1、attempted=h+1、anchor.sequence=events、anchor.registry_head=外部head的pending；当前child根必须不存在，前后root精确拓扑/身份、完整restore、最后intent metadata/source audit payload/event head/source/request/packet audit均核对。已有partial child、journal/anchor推进或clock/config漂移均拒绝。snapshot不认证writer活跃、持锁或quiescence；历史pending只能作为evidence。最终读取后writer仍可能推进，未来controller必须提供live create-owner→Job的一次性handoff，不能据此恢复/重试/native。

独立审查F1指出只返回packet不足以绑定worker上下文；已增加冻结PendingWorkerInput(packet/spec/limits/canonical receipt)，receipt≤2048bytes，绑定parent/declaration、anchor、journal/intent head、hour/source、before、request/packet audit、stage inventory与实现。构造时重验receipt，消费前validate要求外部receipt SHA。writer_lock_authenticated/quiescence_certified/native_execution_authorized/independent_job_integrated/resource/formal均false，external_live_handoff_required=true。

测试历史：primitive短10 passed/1 deselected/39.45s；primitive完整14 passed/124.32s；typed receipt定向3 passed/12 deselected/35.59s；最终根整批19 passed/147.43s/exit0，独立只读 /root/h1_parent_review 19 passed/146.13s/exit0，无开放finding，非official verdict。实际已保存v3 source declaration用于独立Python重建pinned RTS origin、before identity、audit及232stage inventory，writer三个lease仍有效，文件/mtime不变、未创建child；这是0 solver stages的输入验证，不是232stage求解或192小时producer覆盖。future carry使用明确synthetic三stage子归档。

开发检查：results/tables/rq2_h1_parent_snapshot_v1_non_authoritative/development_checks.json，SHA256 fa2479b2f55da31bbc12f91d5a4b5f28312b4ab79181c79bf5cf573b07b933cc，绑定76文件pins，显式包含v3 request.json测试输入。git diff --check通过；旧895/1695封存成员、248/251运行文件及前序68pins无漂移。新native调用0，无新production outer/lease/authority；producer/native_export/collector/independent_hour_jobs/resource/formal_execution_ready/formal_result仍false。

下一步：controller须在创建当前child之前核验typed input并执行新的live handoff，再接独立hour Job和完整worker/native raw-before-audit路径。完整分段/observer、Job/FS/时间及全任务资源、typed missing-tail、实际reuse DAG/task manifest、共同Rref/A和完整LB/UB、封存和全新official独立审查仍未完成；新native须具体就绪包与门禁后另行明确授权。整体目标继续进行。

### 2026-10-04 H1 synchronous saved-worker handoff development v1

新增 experiments/h1_saved_worker_handoff_development_v1.py、对应 tests 及 docs/model_spec/rq2_h1_saved_worker_handoff_development_v1.md。LiveSavedController 内部 create exact bounded parent，不接收旧 owner、reopen token 或 resume。parent guard 与三个 writer lease 全程保持：ready/source/clock/carry → intent journal+anchor → 当前 child 不存在时 snapshot 重建 typed input → 单次内存消费 → 固定 attested child → 完整保存/审计/finish → fresh reopen → source 复核 → outcome journal+anchor → 完整 restore。补齐旧 step_saved 先建 child 导致 snapshot 无法接入的开发断点。

consume 在任何 child mkdir 前标记 used；校验 controller-local receipt SHA、parent/intent/source/request/packet audit/anchor/head，并显式比较 packet/spec/limits。整个 step 禁止 solver 调用。snapshot、receipt、constructor、iterator、finish、fresh reopen、source 及 outcome anchor 前后异常均 poison；部分 raw、完整 child 或未锚定 tail 保留，无补写、清理、二次消费或重试。reentrant close/inspect/step 不释放 live lease。两小时 synthetic 三stage测试从真实前一小时 replay carry 构造第二小时输入；不是 native 或 pinned RTS 全192小时覆盖。

初版根整批 9 passed/242.83s/exit0，初版三文件 snapshot 保留；独立静态审查后补显式值比较、修正 local pin 措辞并增加 fresh-reopen 窗口。最终根定向 4 passed/6 deselected/31.99s/exit0；最终独立只读 /root/h1_parent_review 整批 10 passed/258.44s/exit0，无开放 finding，非 official verdict。测试历史按快照保存，不将初版测试混称最终整批。

开发检查 results/tables/rq2_h1_saved_worker_handoff_v1_non_authoritative/development_checks.json，SHA256 9bdbc977cf7397be32bfb2e66e2f69e384976dd5ced5005e0388a60802538d27，绑定87文件 pins。前序76pins、v2/v3的895/1695封存成员及248/251运行文件无漂移。新 native 调用0，无新 production outer/lease/authority。未新增 handoff 文件或 raw 副本；原条件 saved-path 文件内容界沿用，内存与新增重放时间未证明。旧磁盘归档本身不证明使用了本 controller。

此项仅 synchronous in-process saved handoff；last_input_receipt 是最近成功输入的内存记录，不是持久 journal 或续跑 token。durable_handoff、independent_hour_jobs、producer_coverage_proven、native_export_coverage、collector_integrated、resource_admission、formal_execution_ready、formal_result 仍 false。后续须接新的 durable one-shot 独立 hour Job 与完整 worker/native raw-before-audit、完整分段/observer、Job/scratch/FS/时间资源、typed missing-tail、实际 reuse DAG/full task manifest、共同 Rref/A 与完整 LB/UB，再封存并开展全新 official 独立审查。具体新 native 运行仍须就绪包与门禁完成后另行明确授权；整体目标继续进行。

### 2026-10-04 H1 saved-only independent Job development v1

新增 experiments/h1_saved_job_development_v1.py、experiments/run_h1_saved_job_worker_development_v1.py、tests/test_h1_saved_job_development_v1.py 和 docs/model_spec/rq2_h1_saved_job_development_v1.md。SavedJobController 在独立 outer root 持有 lease；source_parent 与逐hour Job目录互为 sibling，旧parent拓扑及src闭包不变。controller/parent guard覆盖 ready/source/carry、intent+anchor、typed snapshot、Job、fresh child/source复核和outcome全过程。每次请求、PID/creation、初始headroom、release intent、consumption及result均有界持久写入；不存在 reopen/resume/native路线。

固定顺序为 request/launch → 已入Windows Job的suspended child → initial observation/child身份 → 复核parent pending/current child absent与全部pins → release_intent → release/wait。worker校验exact schema、argv/cwd/无license allowlist环境、预算/host/完整process identity及实际PID/creation，先xb/fsync/fresh readback保存consumed，再独立重建typed input并比对receipt，最后运行固定saved-report AttestedChild。父端只在exit0、whole-job-quiescent、无resource/observation error且峰值在界内时读result，之后重验raw来源、fresh科学replay与source，再锚定outcome。release intent不证明运行；consume不证明完成；job_checks不证明后续parent outcome闭合。任何失败保留partial/full证据并poison，无清理/修复/重试。目录断电durability没有声称。

独立审查闭合exact schema、统一false flags和initial headroom重建：有限有序clock，精确commit/disk类型，当前目录/volume身份，同volume demand/reserve/minavailable，以及sufficient=true、reservation/hard/formal=false。全worker禁止solver调用。两次真实Windows Job消费synthetic三stage reports完成两小时carry，第二小时由前一小时科学replay重建；research级independent_hour_jobs门仍false。另默认-I -B入口重建真实pinned RTS origin与232stage inventory后，故意供给无效saved raw，验证先保留raw再拒绝、exit2、无parent outcome；不是完整RTS小时或232stage执行。

测试按真实快照保留：初版2 failed/11 passed/4 deselected/39.92s和诊断1 failed/16 deselected/9.80s源于test-only隔离launcher导入pytest缺pygments；不能视作预定故障窗口已覆盖。仅测试shim显式添加定位到的pytest依赖目录（含pygments/colorama），默认worker不变、环境不安装。修后2 passed/15 deselected/32.61s及中间23 passed/5 deselected/111.61s单列。后续整批1 failed/37 passed/318.36s为3秒deadline先于result marker，保留完整失败快照；修为等待marker后只注入该owner计时年龄，触发真实deadline/quiescence，不放宽实现或科研阈值。最终根新增/修复定向2 passed/37 deselected/33.74s；底层parent-death/descendant-quiescence/failed-wait回归5 passed/31 deselected/3.71s，均exit0。最终独立只读 /root/h1_parent_review 整批39 passed/339.51s/exit0，4文件pins前后相同，无开放finding；非official verdict。

单Job受控文件内容界1062913 bytes、11files、2directories，包含4个256KiB JSON、5个2048-byte JSON、4096-byte诊断和1-byte lease。H192/S232的parent+children+192Jobs+outer lease条件和为54665918210 bytes、630151files、46276directories；补充独立只读算术/作用域审查无finding。此界排除外部source raw、任意scratch、FS metadata/allocation和时间，不能用于完整resource admission。Job目录未新增raw副本，child副本仍在既有parent界内；完整分段/observer与2440秒non-solver分项未证。

开发检查 results/tables/rq2_h1_saved_job_v1_non_authoritative/development_checks.json，SHA256 d637de8ec26ff7cc8fbc4aae708aa8b2fe06fa88b307d5daf6c8ff4828929ab9，绑定107文件pins。前序87pins、v2/v3的895/1695封存成员及248/251运行文件无漂移；git diff --check通过。新native调用0，无新production outer/lease/authority。producer_coverage_proven、native_export_coverage、collector_integrated、independent_hour_jobs_integrated、resource_admission、formal_execution_ready、formal_result保持false。

下一步继续native export与raw-before-audit生产producer/worker接线、完整192小时source/carry覆盖、完整分段/observer、source/raw/scratch/FS/时间及全任务资源、typed missing-tail、实际reuse DAG/full task manifest、共同Rref/A与完整LB/UB，再封存及全新official独立审查。新的具体native运行仍须就绪包与门禁完成后另行明确授权。整体目标继续进行。

### 2026-10-04 H1 complete linear export guard development v1

新增 experiments/h1_linear_export_guard_development_v1.py、tests/test_h1_linear_export_guard_development_v1.py 和 docs/model_spec/rq2_h1_linear_export_guard_development_v1.md。后继只读predicate补齐全部native变量domain/bounds、fixed bounds、完整linear constraints的terms/sense/RHS及objective核对；完整forward/reverse双射、native index和双向sameAs对应，允许同一native对象的不同Python wrapper。拒绝hidden quadratic/SOS/general/scenario/PWL结构、lazy rows、extra/missing variables/rows、duplicate terms、range及精确binary64 rational algebra差异。没有修改旧guard、src、v2/v3合同或report grammar。

独立开发审查及根自检发现两项无限语义漏检：Gurobi把部分达到1e20的finite variable bounds及inequality RHS视作无限/恒满足。修复为所有finite canonical variable bounds和normalized exact Fraction RHS统一abs<1e20；双侧/双符号/全部sense（含equality）均为明确更窄协议，未改变科研阈值或数据。边界测试覆盖±1e20拒绝及nextafter向0最近值通过。exact RHS subtraction有rounding差异仍拒绝，不修补系数。native infinity getter是否返回声明的±1e100尚未live验证，其他表示当前fail closed。

零solver检查构造pinned RTS origin的980rows（339eq/638upper/3lower）及既有synthetic future carry+locks的1272rows（631eq/638upper/3lower），均无range、normalized RHS可精确binary64表示且在新范围内。synthetic_boundary=true、reachable_assignment_proven=false、scientific_witness=false；不是全192小时或actual native export覆盖。

测试历史逐快照保存：初33 passed/0.58s；增加pinned model test后因错误直接调用pytest fixture出现1 failed/33 passed/2.01s，该3文件snapshot及失败记录保留；修fixture后根34 passed/8.37s、独立34 passed/8.80s及相关17项回归仅对应1e20修复前快照，不能作为最终版本结论。修复无限语义后最终根44 passed/8.39s/exit0，独立只读 /root/h1_parent_review 44 passed/8.05s/exit0及17 passed/21 deselected/1.96s/exit0，三文件pins前后相同，无开放finding；非official verdict。

开发检查 results/tables/rq2_h1_linear_export_guard_v1_non_authoritative/development_checks.json，SHA256 7ddb39a20a94da76306d822780640e48a73ac817bbfa2643dfe95caa38e1a031，绑定128文件pins。前序107pins、v2/v3的895/1695封存成员及248/251运行文件无漂移。新native调用0，无新production outer/lease/authority；producer_coverage_proven、native_export_coverage、collector_integrated、independent_hour_jobs_integrated、resource_admission、formal_execution_ready、formal_result仍false。

本predicate尚未接worker；future caller须认证exact adapter、update native model后核验并保持到optimize前不变。旧solve_once在encode raw前已load并做residual audit，不能直接复用为raw-before-audit生产路径。下一步继续拆分原始native输出保存与科学审计、producer/worker接线、完整分段/observer、192小时source/carry与全任务资源、typed missing-tail、actual reuse DAG/manifest、共同Rref/A和完整LB/UB，再封存及全新official独立审查。新的具体native运行仍须就绪包与门禁后另行明确授权；整体目标继续进行。

### 2026-10-04 H1 raw capture before adapter postprocessing development v1

新增 experiments/h1_native_raw_capture_development_v1.py、对应tests及docs/model_spec/rq2_h1_native_raw_capture_development_v1.md。StageCapture为单stage/create-once的版本化producer边界：request/structure/implementation绑定、spec/options记录 → exact direct instance的单次_apply_solver入口 → update与完整linear export检查 → raw intent → 原apply一次 → native原始状态/变量/目标读取并xb/fsync/fresh readback/receipt → 才返回Pyomo DirectSolver.solve进行_postsolve → canonical/native export/recapture及磁盘raw复核 → downstream consumer → close一次及close后metadata/raw复核 → raw finish和complete记录。没有新CLI、production封存或Job/worker连接。

新raw独立schema，不冒用旧runner identity，也不作为旧v3 report输入。原始变量X、native index/name/type/bounds、objective terms和状态/ObjVal/ObjBound/ObjBoundC/Runtime/MIPGap保留；binary64同时存big-endian 16hex位bits与可读float.hex，保留negative zero和NaN sign/payload。微小负generation不在捕获时转换；批准的映射及全约束重验仍须下游科学consumer实施。缺失getter通道保留unavailable及bounded exception class，不伪造0；optional diagnostic缺失不代表数值接受。apply异常在raw保存后重抛；无incumbent不解释为数学不可行。

实现拥有process/thread和nonblocking guard；第二次run/apply及重入不重复native apply，escaping exception poison，不重试/恢复/修补。消费者没有solver handle，known solver entries禁止。close只尝试一次；默认Gurobi全局environment存活与whole-Job quiet须由future controller处理。raw terminal只表示Ingress callback闭合；finish已closed或complete已写出后确认失败时不保证aborted.json存在，owner仍unresolved。complete文件存在本身不构成持久接受；external complete pin与independent fresh reader尚未提供。

独立开发审查闭合5项：close后再次核对binding/spec/export/raw；runtime identity直接绑定继承guard及两版grammar；float bits完整保留；binding/raw/complete统一false flags；finish与complete publication前后故障窗口。初18 passed/4.01s保存两文件snapshot；补secondapply后的根19 passed/4.02s与独立19 passed/3.95s、根相关74 passed/15.49s为pre-fix历史，三文件pre-review snapshot保留。最终根31 passed/5.92s/exit0；独立只读 /root/h1_parent_review 31 passed/5.71s及相关raw ingress+linear guard回归74 passed/15.16s，均exit0、3pins前后一致，无开放finding，非official verdict。

测试使用FakeDirect并借用真实installed DirectSolver.solve，_save_results=False；没有实例化真实Gurobi，未覆盖actual Gurobi _postsolve、_save_results=True符号映射分支、native infinity getter、whole-Job quiescence或完整232×192覆盖。注入外部raw破坏时检测并停止，不修复原文件。新增native raw副本使用16MiB硬入口cap，提取/序列化/写入中断或超cap不保证完整raw；更紧grammar内容界、内存、新增副本全任务磁盘/FS和完整分段时间准入仍缺，不能沿用旧磁盘准入。

最终开发检查 results/tables/rq2_h1_native_raw_capture_v1_non_authoritative/development_checks_v2_final.json，SHA256 2c2dddaf3cce31a443f9b01243597a6404ce8182871508d0fe237eb567400128，绑定145文件pins。首版development_checks.json保留；final revision仅显式增加solver-entry guard依赖pin（原已在旧outer及runtime identity中），3实现/测试/spec字节不变。前序128pins、v2/v3的895/1695封存成员与248/251运行文件无漂移。新native调用0，producer_coverage_proven/native_export_coverage/collector_integrated/independent_hour_jobs_integrated/resource_admission/formal_execution_ready/formal_result均false。

下一步为新native raw格式实现版本化科学consumer和independent fresh replay，绑定原始X与Pyomo结果/完整assignment及approved generation mapping，然后接attested worker、external completion pin/fresh reader、完整计时与独立hour Job。完整source/carry覆盖、实际reuse DAG/full manifest、共同Rref/A、完整LB/UB及资源/official门继续未闭合；新的具体native运行仍须就绪包与全部门禁后明确授权。整体目标保持进行中。

### 2026-10-05 H1 retained native capsule science consumer development v1

新增 experiments/h1_native_raw_science_development_v1.py、tests/test_h1_native_raw_science_development_v1.py、docs/model_spec/rq2_h1_native_raw_science_development_v1.md。新consumer把已保存native capsule接到原有科学判据：fresh canonical模型检查完整native变量/domain/bounds/objective与binary64 bits；postsolve reported rows与合法fixed/unused-unbounded-continuous completions逐位对应原始X；sidecar及receipt在残差/判据/映射之前保存；独立verify_numerical和未改predicate通过后，按已批准v3 generation规则映射并完整重验，保留原始assignment及完整mapping。referenced variables由canonical repn独立重建。新numerical外层标为derived_legacy_predicate_view，旧v3 reader拒绝它，不冒充历史native report。

create-once science root绑定producer request/spec/export及raw ingress链，fresh reader需外部science terminal pin，重建模型并重算全部输出，完整字节/身份前后复核拒绝恢复mtime后的漂移。science terminal仍不代表producer后续close/finish成功，stage_capture_completion_checked=false。拒绝/写入失败保留已有raw/sidecar/receipt；ProjectionRejected保留原receipt；terminal落盘后确认抛错不会返回成功或外部pin，根目录不能retry。

零native证据使用旧assignment的派生test capsule：三个synthetic stages、pinned RTS origin 0/1/231及合成tiny-negative映射；三阶段组合借真实DirectSolver.solve驱动和synthetic adapter（_save_results=False），下一stage使用前阶段新consumer返回lock。没有actual Gurobi/native witness或完整小时执行，actual symbol-map postsolve分支仍待验证。新增sidecar/科学输出、模型clone、重复读取/replay的内存、时间、磁盘/FS须计入后继预算，caps不构成资源准入。

初始33 failed/7.46s为fixture缺_cuid，后1 failed/3 passed/4.11s为bits测试未实际改变bits，初版/失败记录均保留。中间33 passed/17.92s、41 passed/29.27s、单项1 passed/41 deselected/4.88s和根43 passed/33.17s仅对应各自快照。独立43 passed/33.35s发现failure-window测试缺口；三文件pre_failure_window_review_snapshot保留。根仅增加10项测试覆盖拒绝mapping保留、numerical/mapping/result写前与写后确认失败、terminal写后确认失败、producer源在consume/inspect期间漂移。最终根53 passed/40.31s/exit0；独立新增10 passed/43 deselected/8.98s/exit0，相关独立14 passed/68 deselected/4.08s/exit0。根相关raw capture+generation projection共82 passed/18.69s/exit0，对应未变实现。只读R3 pre-seal审查无开放finding，非official verdict。

最终开发检查 results/tables/rq2_h1_native_raw_science_v1_non_authoritative/development_checks.json，SHA256 c3325211000a4ef26a7ea4a55304550ac2436b53622aeaeb589aab06803afb08，绑定171文件pins。前序145pins、v2/v3的895/1695封存成员及248/251运行文件无漂移。新native调用0；全部未提交工作、冻结协议/结果和中间证据保留。producer_coverage_proven、native_export_coverage、collector_integrated、independent_hour_jobs_integrated、resource_admission、formal_execution_ready、formal_result均false。

下一步：externally pinned producer completion与fresh reader握手、完整worker/独立hour Job/分段及observer计时、0..191 source/carry连续覆盖、资源内容界及全任务新增副本预算、actual reuse DAG/full manifest、共同Rref/A与完整LB/UB证书，然后successor封存和全新official独立审查。新的具体native运行仍需就绪包、门禁及明确授权。整体目标继续进行中。

### 2026-10-05 H1 owned stage completion development v1

新增 experiments/h1_stage_completion_development_v1.py、tests/test_h1_stage_completion_development_v1.py、docs/model_spec/rq2_h1_stage_completion_development_v1.md。OwnedStage内部构建stage并创建StageCapture，固定science.consume回调；仅在同owner的StageCapture.run真实返回、返回对象就是callback对象、producer/raw状态成功且guard释放、fresh复核完成后mint不可普通构造的进程内Completion。取得guard后的异常poison；未取得guard的重入/并发调用仅拒绝且不改active owner状态。无retry/resume。

独立inspect需外部producer complete pin、science terminal pin及reader implementation pin，核验root/source containment、17文件/3子目录精确拓扑、raw ingress terminal与producer complete完整链及science fresh replay，并前后复核全部字节/identity/listing/context/implementation。reader仅返回条件证据，producer_run_return_observed=false、whole_job_quiescence_checked=false，不能从磁盘重建live Completion。双pin识别确定性字节，不证明唯一执行实例；Completion为可信Python调用边界，不是对任意Python对象篡改的安全边界。没有新增成功输出文件，新增replay工作及内存仍需计入后继资源预算。

失败窗口验证涵盖science terminal已存在后close失败、raw terminal/producer complete写前及写后确认失败、返回后poison/raw状态不一致或返回对象替换、fresh replay失败、pin/root/request混配、completion/source/目录中途漂移、owner/reentry和dependency漂移。文件完整存在但调用抛错时不返回live receipt。测试使用真实DirectSolver.solve驱动加synthetic adapter和派生saved assignment；没有actual Gurobi或新的native求解。

历史初版handshake设计源码保留，后按设计审查简化为双pin接口；首次22 passed/36.25s快照保留。增加reader implementation pin/root规范化及跨root/目录增长后根24 passed/42.60s。独立静态审查指出spec的Any escaping exception未区分guard取得失败；修spec及reentry测试断言，三文件pre-review快照和finding保留，实现不变。最终根24 passed/42.70s/exit0；独立只读R3最终24 passed/42.48s/exit0，capture/science失败窗口窄回归7 passed/4.72s/exit0，三文件pins前后一致，无开放finding。非official verdict。

开发检查 results/tables/rq2_h1_stage_completion_v1_non_authoritative/development_checks.json，SHA256 97c1286673f4c8a58f8cc624e0b34152241d671468b5f7ed7595ef8ce2e6f242，绑定187文件pins。前序171pins、v2/v3的895/1695封存成员及248/251运行文件无漂移。新native调用0。producer_coverage_proven、native_export_coverage、collector_integrated、independent_hour_jobs_integrated、resource_admission、formal_execution_ready、formal_result全部false，未建立production outer/lease/运行许可。

下一步将owned stage completion接入完整小时worker，完成232-stage lock链、approved mapping后的小时projection与fresh replay，并接完整分段/observer计时、独立hour Job及source/carry parent。实际Gurobi/symbol-map分支、全部0..191小时覆盖、资源内容界及新增副本预算、actual reuse DAG/full manifest、共同Rref/A、完整LB/UB仍缺；需后继封存及全新official独立审查。新具体native运行必须在包与门禁就绪后获得明确授权。整体目标保持进行中。

### 2026-10-05 H1 sequential owned hour development v1

新增 experiments/h1_owned_hour_development_v1.py、tests/test_h1_owned_hour_development_v1.py、docs/model_spec/rq2_h1_owned_hour_development_v1.md。OwnedHour按真实stage_order（1..232）内部创建OwnedStage，要求exact live Completion并fresh inspect后才写create-once commit；确认commit后仅使用fresh-inspected lock推进前缀。binding显式绑定input/source audit/relative hour、spec/limits/order和implementation。commit绑定previous head、index/child、stage request/implementation、进入lock hash、双pin与科学结果摘要。失败停止，无retry/resume/partial-hour结果。

全序列完成后先从空locks独立重验全部stage/commit链，最终fresh assignment仅交既有approved replay_feasible_boundary生成新schema projection。新projection绑定before/after、locks、完整stage双pin/commit vector、generation规则与新implementation；不构造旧v3 projection类型或冒充旧raw report。全链prepublication replay通过后写projection/terminal，再全链fresh inspection通过才返回HourCompletion。reader需外部hour terminal及implementation pins，前后核验全部目录/文件hash+identity/source audit/clock/context；reader不能从磁盘重建owned成功返回证明。publication确认失败可留字节，但没有live hour receipt。

验证包括完整三阶段synthetic adapter pipeline，与旧v3 oracle的network/completed_hours/units/locks核心值一致；stage成功但fresh失败、commit写前/写后、projection/terminal写前/写后失败、断链/prefix/request/双pin/child/topology/源identity漂移、全链中途同长度字节变化恢复mtime、非live stage结果、owner/reentry与dependency边界。初23 passed/91.99s快照及初始设计源码保留。最终根28 passed/104.79s/exit0；独立只读R3 28 passed/103.07s/exit0，三文件pins前后一致，无开放finding。pinned RTS仅检查真实232-stage声明；没有运行232-stage长链或actual native solver。非official verdict。

受控文件cap算术另存controlled_content_cap_arithmetic.json并经独立复核：每stage 17文件共34365440 bytes；S=232含commits/binding/projection/terminal共7973523456 bytes、4179 files、931 directories（含root），即232*34365440+232*2048+2*2048+262144。此为列明入口cap的受控内容算术，不是conditional grammar证明或完整资源准入；排除native scratch/log、外部输入、FS分配、内存及序列化buffer、timing/Job/controller/parent产物。旧磁盘预算不能沿用，重复science replay时间也未准入。

开发检查 results/tables/rq2_h1_owned_hour_v1_non_authoritative/development_checks.json，SHA256 c7df90c811fbc13a8c07cadf65182cb37dc74675429852cc224b255ae07b0c54，绑定201文件pins。前序187pins、v2/v3的895/1695封存成员及248/251运行文件无漂移。新native调用0；全部未提交工作及冻结协议/结果保留。producer_coverage_proven、native_export_coverage、collector_integrated、independent_hour_jobs_integrated、resource_admission、formal_execution_ready、formal_result均false。

下一步接完整分段durable timing/独立observer、完整worker与独立hour Job、source/carry parent；actual Gurobi/symbol-map分支、232-stage实际执行及0..191连续carry覆盖、条件内容界/全任务预算、actual reuse DAG/full manifest、共同Rref/A与完整LB/UB仍待完成。之后才能后继封存、全新official独立审查，并对具体新native运行取得明确授权。整体目标保持进行中。

### 2026-10-05 H1 exact optimize-call timing boundary development v1

新增 experiments/h1_native_call_timing_development_v1.py、tests/test_h1_native_call_timing_development_v1.py、docs/model_spec/rq2_h1_native_call_timing_development_v1.md。核对installed源码发现_apply_solver含参数/log/stale等非solver工作，而旧durable Journal.span在begin文件fsync/readback前取tick，会把begin I/O计入native。两者不能直接作为whole-worker wall中扣除的native时间，否则低估non-solver。本单元修复精确调用边界前置条件，尚未接完整worker。

显式versioned apply副本固定Pyomo6.10.1、gurobi_direct.py SHA cef4ef2bc51d819a83ad4a3ce467fb6cbde6594b201c8ee34e9649953cf451e6、原apply source和_set_options source pins。去掉唯一measurement.invoke后AST与installed apply完全相等，保留参数过滤、suffix、log reset等顺序；真实model身份不变，不用facade/实例native方法替换。Pyomo版权及BSD-3-Clause条件全文随复制实现保留。installed漂移在solver调用前拒绝。

顺序：binding → apply start → setup/options → optimize intent写盘/fsync/readback → native start → optimize(None)一次 → native end → completion持久化 → apply tail → apply end → terminal与fresh inspection。intent/completion I/O均在native区间外、apply窗口内。模拟优化73ns，intent和completion各延迟1000ns时native仍73ns，non-native apply为2022ns。边缘clock读取/校验/Python调用开销属于声明的外部调用边界，不冒充Gurobi Runtime或纯C算法时间。

未知状态保持fail closed：optimize异常、clock回退、intent/completion/terminal写前或写后确认失败、tail异常均不返回成功timing receipt；残留完整文件不证明owned调用成功返回，不重试。canonical root/普通目录identity在创建及调用前检查、reader全视图前后复核，避免原本可能到optimize后才拒绝alias的路径。可信Python接口不是任意module/object篡改的安全边界。4份metadata共8192 bytes内容cap不包含其他worker成本。

首次21 passed/1 failed/2.47s为注入lambda源码引起SyntaxError未归一化，初始快照保留；修为ValueError后22 passed/2.15s快照保留。独立pre-seal指出许可保留和root前置拒绝，两项修复后最终根24 passed/2.15s/exit0，独立只读R3 24 passed/2.06s/exit0，三文件pins前后一致、无开放finding；非official verdict。所有测试使用fake model，三条独立synthetic interval不是三阶段完整timed hour，更不是actual Gurobi验证。

开发检查 results/tables/rq2_h1_native_call_timing_v1_non_authoritative/development_checks.json，SHA256 5d8bb9a4bd7e48d35989d44e5d2aa4e2ab867aa7fc20d3dd1c5a30fd1a898d6a，绑定218文件pins（含installed vendor文件及许可）。前序201pins、v2/v3的895/1695封存成员及248/251运行文件无漂移。新native调用0。

下一步将此边界接入版本化timed capture/science/hour，计量其余完整phase与独立observer，并接worker/独立hour Job和source/carry parent。binding构造、terminal/review、worker其他阶段、controller/Job等待仍在本apply窗口外，必须纳入外层non-solver计量；instrumentation_coverage_verified、component_budget_verified、resource_admission、formal_execution_ready、formal_result仍false，不能证明2440秒分项预算。actual Gurobi/symbol-map、232-stage实际执行/192小时carry、资源/任务DAG/manifest/Rref/A/LBUB及新official审查仍待完成。新native运行需具体就绪包和明确授权；整体目标保持进行中。

### 2026-10-05 H1 native-timed hour successor development v1

新增 experiments/h1_timed_native_capture_development_v1.py、experiments/h1_timed_native_science_development_v1.py、experiments/h1_timed_stage_development_v1.py、experiments/h1_timed_hour_development_v1.py，以及 tests/test_h1_timed_hour_development_v1.py 和 docs/model_spec/rq2_h1_timed_hour_development_v1.md。四层版本化后继将精确optimize调用计时接入raw/science/stage/hour链；旧实现及封存成员保留。11项science核心函数AST与旧版本相等，approved generation转换及全部科学谓词不变。

capture持有同request/index的Measurement；仅接受owned调用返回的binding/terminal/completion pins，固定四份计时文件完整bytes/identity视图，后续复核不得重新hash以采纳漂移。science要求live capture传入外部pins，stage检查21文件及capture/science/timing一致性；hour commit、projection和terminal绑定完整timing vector与各完整区间之和。各区间在各自clock domain内求差，不跨域相减，也未推导whole-worker non-solver时间。计时terminal可先于raw存在；此时发生中断或raw capture失败仍是unknown witness，不能产生成功stage/hour或重试。apply/timing异常尽力保存原native channels和错误后停止。

初版23 passed/60.46s及源码快照保留；最终根29 passed/67.88s/exit0，独立只读R3合并53 passed/68.59s/exit0，无开放finding，非official verdict。测试使用installed DirectSolver.solve、pinned timed apply body、synthetic native model和注入clock。完整三阶段assignment/mapping/lock及hour边界与既有oracle一致；三个73ns区间合计219ns仅为测试fixture，不是native性能实测。故障覆盖timing、raw、science、close、stage/hour publication写前写后及live pin漂移；无新actual native调用。

受控内容cap每stage增加4份2048-byte metadata和一个目录。232 stages合计7975424000 bytes、5107 files、1163 directories（含root）；排除native scratch/log、外部输入、FS分配、内存、其他phase journal及worker/controller/parent/Job成本，仍不是完整资源准入。

开发检查 results/tables/rq2_h1_timed_hour_v1_non_authoritative/development_checks.json，SHA256 0cb1bd422161f02f8671e4a02d478220f21a10024d58374b679478ddd7f09c61，绑定236文件pins，本次fresh核验一致。前序218pins及v2/v3的895/1695封存成员、248/251运行文件保留核验证据见preservation.json。当前无相关求解进程。全部未提交文件及冻结协议/结果保留。

下一步完成其余phase、worker生命周期与独立Job observer计量，再接完整worker/独立hour Job及source/carry parent。actual adapter、完整232-stage及0..191连续carry、条件grammar/新增副本资源预算、actual reuse DAG/full manifest、共同Rref/A及完整LB/UB仍待完成。producer_coverage_proven、native_export_coverage、collector_integrated、independent_hour_jobs_integrated、instrumentation_coverage_verified、observer_overhead_separated、component_budget_verified、resource_admission、formal_execution_ready、formal_result保持false；未证明2440秒non-solver预算。后续须successor封存及全新official独立审查，具体新native运行仍需明确授权。整体目标继续进行中。

### 2026-10-05 H1 lifecycle timing coverage gap audit development v1

新增 experiments/h1_lifecycle_timing_gap_audit_development_v1.py、tests/test_h1_lifecycle_timing_gap_audit_development_v1.py、docs/model_spec/rq2_h1_lifecycle_timing_gap_audit_development_v1.md。真实durable Journal的无求解合成反例：100ns主体加1000ns terminal写盘与2000ns fresh inspection，返回recorded=100ns，外层enclosing=3100ns，遗漏tail=3000ns。数值来自注入clock，不是性能实测。证明现有journal终点不能覆盖其自身最终持久化与复核。

五份源码hash及AST函数定位存于coverage_audit.json。静态核对Job elapsed始于initial headroom/child creation前，止于whole-Job quiet及exit/peak/identity查询后；不含调用方request/launch准备、wait后close、observation持久化、结果fresh检查和parent outcome。该结论是源码审计，尚非完整runtime integration。下一步实现应从controller transaction外层envelope入手，再桥接worker native区间的clock rate/units、owner/Job、顺序不重叠及真实包含关系；native_total<=wall不能替代此证明。observer与worker重叠耗时不能顺序相加或从non-solver扣除；最终计量receipt自身写盘须另列observer tail并纳入资源边界。随后再在此完整外层窗口内添加phase attribution，避免先把局部journal宣称为完整预算证据。

根定向9 passed/0.19s/exit0；独立只读R3合并25 passed/0.51s/exit0，三文件pins测试前后一致，五份源码定位核验一致，无开放finding；非official verdict。新native调用0。前序236pins、v2/v3 outer895/1695成员和run248/251文件fresh核验无漂移，全部未提交与冻结产物保留。开发检查 results/tables/rq2_h1_lifecycle_timing_gap_v1_non_authoritative/development_checks.json，SHA256 d5e959bb38869908bf39d4d844fe5e79cdaa726211ffd4c65ea1e5fce1f68845，绑定247pins。

此单元仅关闭计时缺口定位与后继边界审查，未完成worker/observer/Job集成或2440秒预算证明。runtime_integration_verified、instrumentation_coverage_verified、observer_overhead_separated、component_budget_verified、resource_admission、formal_execution_ready、formal_result保持false；其余科学覆盖、全任务资源/DAG/manifest/Rref/A/LBUB、封存及全新official审查仍待完成。新native运行需就绪具体包和明确授权。整体目标继续进行中。

### 2026-10-05 H1 saved controller transaction timing development v1

新增 experiments/h1_controller_timing_development_v1.py、tests/test_h1_controller_timing_development_v1.py、docs/model_spec/rq2_h1_controller_timing_development_v1.md。TimedSavedController调用未改动的saved-only controller transaction与cleanup，分别观察初始化、step transaction、close窗口。step外层覆盖intent、source/carry准备、request/launch、Job创建及release、worker启动/工作/退出、whole-Job quiet、fresh结果检查和parent outcome及最终restore；terminal写盘和fresh确认另计confirmation tail。既有Job elapsed仅作诊断，不相加、不扣减native。caller setup、调用间隙及最后live receipt构造/返回后的成本未覆盖，不能称完整program预算。

binding绑定controller PID/thread、clock domain、implementation和声明hours。固定bytes/identity、bounded目录、guard、跨调用单调tick、逐hour前驱链及外部pins阻止漂移与越界创建。reader只检查当前hour计时及Job引用，scientific_replay_verified/prefix_verified/live_return_observed均false，不能恢复live tail或继续执行权限。Observation显式record_kind/index/outcome_head/record_sha256；新step清除旧last_observation。base已成功发布parent outcome后，外层terminal或确认仍可能失败；此时保留outcome但poison wrapper/parent，无新live observation、不重试。

独立timing-root NTFS lease覆盖base close释放outer lease后close.json的写盘与复核，之后才释放timing lease并取live最终tick。固定_Lease.close在finally释放stream/registry，即使unlock报错；wrapper先detach引用再close，避免异常cleanup重复关闭旧owner并移除新owner registry。验证覆盖close写前写后、固定unlock前后故障，以及旧owner释放后新owner取得lease再发生确认失败；也用独立Python进程验证outer lease已释放的close-write窗口内timing lease仍阻止并发重开。无新native调用。

初版13 passed/1 failed/5.12s为测试root缺少_non_authoritative后缀，未启动Job，源码快照保留；修后14 passed/27.91s。扩展18 passed/58.00s后自检修复declared-hours越界先写intent问题，定向1 passed/18 deselected/2.59s。独立审查指出close lease和receipt语义，修后23 passed/61.38s；进一步修复close registry ABA语义，最终根窄回归21 passed/3 deselected/6.84s/exit0。最终独立只读R3全24 passed/62.29s/exit0，三文件pins前后一致，无开放finding；包含三个真实短saved Jobs（成功、worker exit7、parent outcome后outer terminal确认失败）和独立lease探针。全部历史快照及finding保留，非official verdict。

新增受控内容界H=192为792577 bytes、388 files、193 directories，包含timing execution.lock一字节；排除旧controller/Job/parent/child、FS分配、内存、外部输入、scratch及native logs。开发检查 results/tables/rq2_h1_controller_timing_v1_non_authoritative/development_checks.json，SHA256 c09b4fc7d7a0726e903257d835ac3ac78a6a4d2dacff5103593efa716493b551，绑定273pins。前序247pins及v2/v3 outer895/1695、run248/251文件fresh核验无漂移；全部未提交及冻结产物保留。

下一步将timed native hour接入successor worker/controller，证明native区间clock rate/units、owner/Job及真实包含关系，再接worker phase和独立observer重叠计量、caller lifecycle/最后live return tail。producer_coverage_proven、native_export_coverage、collector_integrated、independent_hour_jobs_integrated、instrumentation_coverage_verified、observer_overhead_separated、component_budget_verified、resource_admission、formal_execution_ready、formal_result均false。完整232-stage/192小时source-carry覆盖、资源/DAG/manifest/Rref/A/LBUB、封存和全新official独立审查仍待完成，具体新native运行仍需明确授权。整体目标继续进行中。

### 2026-10-05 H1 owned timed worker-hour envelope development v1

新增 experiments/h1_timed_worker_hour_development_v1.py、tests/test_h1_timed_worker_hour_development_v1.py、docs/model_spec/rq2_h1_timed_worker_hour_development_v1.md。OwnedWorkerHour内部构建既有timed OwnedHour，要求exact live HourCompletion及owner成功状态，然后完整fresh science replay才发布worker terminal。绑定实际Windows PID/creation FILETIME/thread与外部controller request SHA；该SHA只是调用方链接，尚不证明release/consume或Job membership。没有CLI或Job launcher，真实native-capable调用仍需具体包、资源/Job监督与新授权。

本地clock合同核验Windows CPython、retained builtin perf_counter_ns、monotonic/non-adjustable QPC profile、Measurement.__init__及其默认clock未替换；既有capture不传自定义clock。全部stage PID/thread须与worker一致，序号完整、clock标签互异，apply区间有序不重叠、包含native区间且落在constructor-entry/end-tick窗口内。native总量同时绑定stage/hour/worker vector与terminal；worker_window_non_native_ns=(end-start)-sum(native_end-native_start)。此为可信Python本地默认clock合同下的局部差值，不由小于wall的总数推断包含关系，也不证明跨进程clock或真实native来源。

end tick之后的最终算术、terminal写盘、fresh worker inspection、完整hour snapshot复核及lease释放计入live confirmation_tail_ns；最后tick不持久化，随后receipt构造/guard release/调用方/退出仍在窗口外，模块import/startup也在窗口外。reader只返回条件证据，clock_source_authenticated/owned_run_return_observed为false且tail未知。private-token Completion仅由owned成功run返回local_clock_binding_checked=true，全部资源/正式/运行授权flags仍false。

独立pre-seal发现两项：外层inspect返回后只复查timing不足以覆盖science/commit晚漂移；worker固定lease失败窗口缺测。已在conditional reader及owned completion前加入完整hour snapshot前后对比，并加入science/result.bin及commit同长度/恢复mtime漂移、固定LK_UNLCK前后故障、旧owner释放后新owner接管registry ABA验证。hour已成功仍不能绕过worker后续失败；所有证据保留，poison且不返回Completion、不重试。lease沿用detach-before-close，避免finally重复关闭旧owner影响新owner。

初版根21 passed/124.54s/exit0。新增定向测试一次插入位置错误导致NameError，2 passed/1 failed/20 deselected/2.50s快照保留；测试修正后3 passed/20 deselected/2.08s。R3 findings修复后最终根28 passed/224.08s/exit0；独立只读R3最终28 passed/223.32s/exit0，三文件pins前后一致，无开放finding，非official verdict。使用synthetic adapter及真实Windows process/QPC，完整三阶段projection与旧saved oracle一致；没有真实native/solver/Job或232-stage执行。

新增受控内容仅两份<=2048-byte metadata和一字节execution.lock：4097 bytes、3 files、1 wrapper directory，不含既有hour子树、内存/vector、FS分配、外部输入、scratch/logs及controller/observer/lifecycle。开发检查 results/tables/rq2_h1_timed_worker_hour_v1_non_authoritative/development_checks.json，SHA256 63b336783fb98ea5a528f384e32eeff60c76975cdbef5cd5c8c1cde2c77d47f0，绑定293pins。前序273pins及v2/v3 outer895/1695成员、run248/251文件fresh核验无漂移；旧协议、全部未提交和历史测试/finding快照保留。

下一步接successor worker entry和独立Job/controller，核验request/release/consume、实际Job membership及跨进程clock/containment bridge，再补完整phase/observer/startup/exit/caller/return-tail。worker_job_membership_verified、cross_process_clock_bridge_verified、producer_coverage_proven、native_export_coverage、collector_integrated、independent_hour_jobs_integrated、instrumentation_coverage_verified、observer_overhead_separated、component_budget_verified、resource_admission、formal_execution_ready、formal_result均false。完整232-stage/192小时覆盖、条件grammar/资源、actual DAG/manifest/Rref/A/LBUB、封存及全新official审查仍待完成，2440秒预算未证明。新native运行仍需具体就绪包与明确授权。整体目标继续进行中。

### 2026-10-05 H1 released timed worker development v1

新增 experiments/h1_timed_released_worker_development_v1.py、tests/test_h1_timed_released_worker_development_v1.py、docs/model_spec/rq2_h1_timed_released_worker_development_v1.md。开发 API 将 released request 接到既有 OwnedWorkerHour，校验 canonical request、implementation/source/anchor/pending/input receipt、实际 Windows PID/creation FILETIME、argv/cwd/environment、budget/host、release/launch/child/initial observation。exclusive consumed 写盘/fsync/稳定复读后才重建 source/carry；request/release/launch/child/initial/consumed 的固定 bytes/identity 在重建和发布前后复核。已有 DevelopmentNormalChild suspended-create 使用精确 process/Job handles 的 IsProcessInJob 和不可继承句柄检查，本轮复用而未重做。

owned worker 成功后要求 exact live Completion，完整 fresh hour science replay，再 fresh reopen parent snapshot。完整 worker metadata/lock/hour science/commit/timing/projection 的文件与目录 snapshot 包围最终 inspect/source/result write；晚漂移拒绝。worker_result 绑定 request/consume/input receipt、实际进程、worker binding/terminal/implementation 和 projection SHA，返回前再次按 pin 复读。结果文件存在不证明成功返回、exit0 或 parent acceptance。本单元无 CLI、生产 controller、parent outcome 路由；真实 native-capable调用仍需具体包、Job/resource 监督与新的明确授权。

根首轮6 failed/2 passed/21.06s：测试 host request 漏列独立 scratch DirectoryDemand，被检查在 Job 创建前拒绝，无 native，原快照保留。补齐后8 passed/149.11s；加入开发 root guard/结果最终复读后9 passed/148.96s/exit0。独立pre-seal指出三类持久化失败窗口缺测，补 consumed 完整写盘后抛错、worker_result 完整写盘后抛错、最终结果 pin-read 失败；根新增定向3 passed/9 deselected/75.21s/exit0。consumed write-after 保留记录且 source/worker 未启动；后两者可保留完整结果但 execute 不返回成功、child 非零退出。全部再次消费被 FileExistsError 拒绝。初报规格编码问题经双方 Unicode escape 核验撤销：原始和最终文件均为正确 UTF-8，乱码来自控制台显示链；历史报告/快照照保留。

最终独立只读 R3 全12 passed/218.50s/exit0，三文件测试前后pins一致，无开放 correctness finding，非official verdict。9项使用真实受控短 Windows Job、synthetic loader/adapter、真实PID/QPC，零真实 native/solver。成功与全部失败路径的 parent 均只有一条intent并保持 pending_unknown，没有 parent outcome。未重复运行未改的前序28项worker-hour测试；终态无相关进程。

consumer 新增两份各<=262144-byte文件：条件逻辑内容界524288 bytes、2 files、0 additional directories，排除既有worker/hour、caller records、root lease、scratch/logs、外部source、内存和FS分配。小型合成Job的预算不能替代全研究资源准入。开发检查 results/tables/rq2_h1_timed_released_worker_v1_non_authoritative/development_checks.json，SHA256 f1df59f995cd750bac1f0c4f28e37a83a32fd2e64e0f7942984a096c0e2d483b，绑定309pins。前序293pins与v2/v3 outer895/1695成员、run248/251文件fresh核验无漂移，全部未提交、旧协议、冻结和历史产物保留。

下一步：实现successor Job/controller的完整worker输出验收和parent outcome接续，再完成跨进程clock containment、完整phase/observer/startup/exit/caller/return-tail计量。producer_coverage_proven、native_export_coverage、collector_integrated、independent_hour_jobs_integrated、worker_job_membership_verified、cross_process_clock_bridge_verified、instrumentation_coverage_verified、observer_overhead_separated、component_budget_verified、resource_admission、formal_execution_ready、formal_result、native_execution_authorized均false。完整232-stage/192小时source-carry覆盖、新增副本资源预算、actual reuse DAG/manifest/common Rref/A/full LB/UB、封存及全新official独立审查仍待完成；2440秒分项预算未证明。新的具体native运行仍需明确授权，整体目标继续进行中。

### 2026-10-05：timed Job controller / source parent 开发复审闭合

新增 experiments/h1_timed_job_parent_development_v1.py、h1_timed_job_snapshot_development_v1.py、h1_timed_released_worker_development_v2.py、h1_timed_job_controller_development_v1.py，以及对应 test_h1_timed_job_controller_development_v1.py 和 rq2_h1_timed_job_controller_development_v1.md。根代理唯一写入，旧 src、冻结协议、历史结果和此前开发 pins 保留。新 parent/child protocol 与旧 saved-only 路由隔离；released-worker v2 保留 v1 算法，仅切换 snapshot 和共同 implementation identity。

controller 每小时使用独立 suspended Windows Job，绑定 request/launch/child/initial/release；实际 typed exit0、whole_job_quiescent 和资源观察检查后才读取 worker result。父端重新核对 pinned source/carry，完整 fresh science replay，并用全部受控 Job evidence byte/identity view 包围 reference、outcome 和返回。原 generation witness、差值、批准映射及全部约束审计保留；连续 carry 只取经完整复核的 timed projection。任意失败 poison、不重试；结果或 accepted event 已落盘不代表 step 成功返回。关闭先 detach owner，再尝试全部清理，防止二次 close 影响后来 owner。

根初轮 1 failed/37.82s：检查器读取持有中的 Windows Job lock 被拒绝，改为固定 identity/size 检查，失败快照保留。随后 5 passed/251.63s；故障矩阵扩展后 quick 14 passed/15 deselected/8.30s（后续增补前历史状态）、主选择 16 passed/14 deselected/680.06s。补 parent_updates 资源登记及 wait/inspect reach 断言后，定向 5 passed/25 deselected/97.98s，均 exit0。独立只读 R3 最终完整 30 passed/683.83s/exit0，六份候选测试前后 SHA256 一致，无开放 pre-seal finding，终态无相关进程。按测试路径静态计数为 16 次受控 Job 创建、15 次 release；这不是 runtime instrumentation 计数。全部 synthetic adapter，零真实 native。

每 Job 的条件逻辑内容界：3 stages 为 105494530 bytes/81 files；232 stages 为 7977525250 bytes/5119 files。parent_updates 另登记 856065 bytes，覆盖 reference、保守单事件 journal 与下一 anchor record；既有 intent/anchor 已在该次 headroom 检查前落盘。scratch、FS 分配、模型和 replay 峰值内存、完整生命周期时间等仍需另行准入。job_view 保留有限 records 与逐文件 hash/identity/cap，不常驻全部 raw；磁盘界不代表内存界。

开发检查：results/tables/rq2_h1_timed_job_controller_v1_non_authoritative/development_checks.json，SHA256 e450cc2f28765b4ee6592384365eebabeae518d20f926923ddb4acb425ecb776，绑定 339 pins。前序 309 pins、v2/v3 outer 的 895/1695 成员和 run 的 248/251 文件 fresh 核验无漂移；初版、五项和十六项快照及历史失败证据全部保留。

下一步接通 controller/worker 跨进程 clock containment，补完整 phase/observer/startup/exit/caller/return-tail 计量；2440 秒 non-solver 分项预算仍未证明。完整 232-stage/192-hour source-carry 覆盖、全资源准入、实际复用 DAG/全任务 manifest/common Rref/A/full LB/UB、successor 封存与全新 official 独立审查仍未完成。producer_coverage_proven、native_export_coverage、collector_integrated、independent_hour_jobs_integrated、worker_job_membership_verified、cross_process_clock_bridge_verified、instrumentation_coverage_verified、observer_overhead_separated、component_budget_verified、resource_admission、formal_execution_ready、formal_result、native_execution_authorized 均保持 false。本次开发审查闭合不等于 official verdict 或运行许可；具体新 native 运行仍需新的明确授权，整体目标继续进行中。

### 2026-10-05：Job clock bridge 开发复审闭合

新增 experiments/h1_job_clock_bridge_development_v1.py、tests/test_h1_job_clock_bridge_development_v1.py、docs/model_spec/rq2_h1_job_clock_bridge_development_v1.md。根代理唯一写入，旧 src、协议、冻结结果及已闭合开发文件保留。新版 Controller 以独立 outer guard 串行 step/inspect/close；原 Job/source/carry/science 事务继续使用已闭合实现。clock profile 采用受信 Windows CPython >=3.10 system-wide QPC 合同，并核对 builtin/default clock、完整 profile、同机实际 Job PID/creation 和整数 ns 区间包含。Python/Microsoft 官方依据已链接于规格；profile 匹配不替代 live Job 身份链或物理时钟误差证明。

bridge intent → 原 parent intent/Job → bridge job.json → 原 parent reference/outcome → bridge terminal → fresh science/parent/计时复核 → live Observation。Job envelope 包含原 _job 的创建、释放、whole-Job静止和完整验收；worker core window 与完整 worker lifecycle 明确区分。记录绑定 parent identity/input head/source、八份Job pins、worker证据链、outcome/head/历史anchor和前一terminal。只在严格包含时计算 observed_non_native_ns=transaction_wall_ns-actual_native_total_ns；confirmation tail 单列live值，最后tick后的返回/caller、初始化、close等仍非完整计量。step 返回原parent result，新增live凭据为 last_observation。fresh reader仅验证单小时及立即前驱条件证据，完整 clock/parent prefix 未由它证明。

持久化失败矩阵已覆盖 job/terminal 写前写后、最终读、晚Job漂移、最后live tick、job.json之后原source失败、并发入口拒绝及close/registry ABA。parent outcome 已提交后计时失败可保留完整parent记录，但 successor poison、无Observation、禁止重试。新增headroom检查要求exact typed observation、request identity和五个false authority flags；只是live同卷需求观察，fresh reader无法证明该次观察或资源预留。

首两次测试setup分别漏supplied和saved fixture，均2 passed/1 error（1.91s和1.83s）、无Job，快照保留。补齐后根完整10 passed/505.27s/exit0；审查补项后根定向7 passed/10 deselected/179.52s/exit0。独立完整17 passed/679.91s/exit0对应精确profile修复前快照，原成功和失败矩阵均有覆盖。随后修复Python dict相等把True/1、False/0视为相等的问题：四处clock匹配统一canonical io.same，增加保留旧Job pins且重签bridge链的monotonic=1、adjustable=0反例。根最终定向1 passed/16 deselected/70.17s；独立同项1 passed/16 deselected/69.48s，均exit0，覆盖正常受控Job及完整reader反例。其余16项未重复运行，结合静态差异复核闭合本单元；不把此前17项冒称最终字节的全量重跑。最终三pins前后一致、无开放pre-seal finding、无相关残留进程，零真实native；非official verdict或运行许可。

资源条件界为(1+3H)*262144+1 bytes、2+3H files、1+H directories；H=192为151257089 bytes/578 files/193 directories，仅新增clock子树。逐step同卷观察合并当前Job内容、parent_updates、剩余clock records与scratch，FS分配、峰值内存、全部运行时间仍未准入。开发检查 results/tables/rq2_h1_job_clock_bridge_v1_non_authoritative/development_checks.json，SHA256 f2c1abe2cec77c93821a270c400b96e7d484663899134de5697caaa3bc820c67，绑定362pins。前序339pins、v2/v3 outer895/1695成员及run248/251文件fresh核验无漂移，全部初版/失败/复审前快照保留。

新确认的预算语义缺口：旧 normal_h1_full_resource_contract.py 的non_solver allowance包括solver TimeLimit overshoot；bridge observed_non_native扣除了实际native全部时间，不能直接当作旧2440秒账本值。后继须绑定同一stage向量的reserved solver allowance并处理overshoot归属，同时完成完整phase/observer/startup/exit/caller/return-tail计量。未更改旧合同或阈值。

producer_coverage_proven、native_export_coverage、collector_integrated、independent_hour_jobs_integrated、worker_job_membership_verified、cross_process_clock_bridge_verified、instrumentation_coverage_verified、observer_overhead_separated、component_budget_verified、resource_admission、formal_execution_ready、formal_result、native_execution_authorized均保持false。完整232-stage/192-hour覆盖、全资源准入、实际复用DAG/任务manifest/common Rref/A/full LB/UB、successor封存及全新official独立审查仍待完成。具体新native运行仍需新的明确授权，整体目标继续进行中。

### 2026-10-05：overshoot accounting 开发复审闭合

新增 experiments/h1_overshoot_accounting_development_v1.py、tests/test_h1_overshoot_accounting_development_v1.py、docs/model_spec/rq2_h1_overshoot_accounting_development_v1.md。根代理唯一写入；旧src、bridge、resource contract、冻结及历史产物均保留。新模块是只读零native reader，仅返回条件内存账目，无writer、运行入口、resume或预算PASS。

复用旧v3资源合同validate_work，按同一完整canonical stage_order取得精确Fraction(time_limit_seconds)，乘10^9仍保留有理数，不round/floor。绑定外部bridge binding/intent/terminal、完整Job/science、逐stage specification/binding/options及QPC interval vector。分析前后固定完整hour_request、spec bytes、stage order、clock root/hour目录identity、全部相关文件views及implementation闭包；report显式绑定hour_request。声明TimeLimit与固定apply路径不等于native实际硬限时认证；这是一项未声称能力，不新增旧合同之外的硬TimeLimit前置门槛，原合同允许overshoot并使用whole-Job限额。

令W为观察窗口、A_i为各stage实际native区间、T_i为各call预留。outside=W-sum(A_i)。aggregate=max(0,sum(A_i)-sum(T_i))允许借用其他stage未用额度，只作descriptive lower bound；逐stage sum(max(0,A_i-T_i))遵守no-sharing语义，outside加该值才是contract candidate。A=[6,0]、T=[5,5]时聚合overshoot=0、逐stage overshoot=1，不能用前者掩盖单call超时。窗口仍缺confirmation/return/close/caller等生命周期及observer覆盖，因此不比较2440阈值，不声称完整non_solver账本已验证。

根首轮19 passed/73.74s/exit0；独立静态指出调用方内存输入可能漂移，补完整request/spec/order前后重验和目录identity，加入有效JSON options.TimeLimit同长度/恢复mtime漂移、最终readback后spec漂移及保留文件identity替换hour目录，根19 passed/85.03s/exit0。最终将内存反例扩到limits.max_constraints，根定向1 passed/18 deselected/88.09s/exit0。独立只读R3最终完整19 passed/88.80s/exit0，其中18项纯算术/反例、一项真实受控短Windows Job加synthetic adapter；零真实native。三份最终候选测试前后SHA一致，无开放pre-seal finding，无相关残留进程；不是official verdict或运行许可。

开发检查 results/tables/rq2_h1_overshoot_accounting_v1_non_authoritative/development_checks.json，SHA256 7693f5b35aa2a89a34e7a9d0faf4cab8bb964e88462dd28202c0679cd1e91499，绑定380pins。前序362pins、v2/v3 outer895/1695成员及run248/251文件fresh核验无漂移；两轮快照和初版检查JSON均保留。内存报告编码cap为262144 bytes，不构成全任务存储、内存或时间准入。

下一步仍需完整phase/observer/startup/exit/caller/return-tail计量，并把同stage预留/overshoot放入完整生命周期2440账本。完整232-stage/192-hour source-carry覆盖、全资源准入、实际复用DAG/任务manifest/common Rref/A/full LB/UB、successor封存及全新official独立审查仍待完成。producer_coverage_proven、native_export_coverage、collector_integrated、independent_hour_jobs_integrated、worker_job_membership_verified、cross_process_clock_bridge_verified、instrumentation_coverage_verified、observer_overhead_separated、component_budget_verified、resource_admission、formal_execution_ready、formal_result、native_execution_authorized均保持false。新的具体native运行仍须明确授权；整体目标继续进行中。


### 2026-10-05：固定 lifecycle driver 开发复审闭合

新增 experiments/h1_lifecycle_driver_development_v1.py、tests/test_h1_lifecycle_driver_development_v1.py、docs/model_spec/rq2_h1_lifecycle_driver_development_v1.md。根代理唯一写入；组合现有 bridge/controller，不改旧 src、worker、封存协议或历史结果。外部固定 H 个 source identities，controller 同时声明 H；仅按前一 live outcome head 顺序推进。入口 QPC tick 覆盖 root/controller 构造、逐小时完整事务、fresh overshoot、最终完整 parent/source prefix replay 和 controller close。主账只用连续 end-start，扣一次完整 native 区间，再加逐 call Fraction overshoot；未知和未细分工作全部留在 non-solver 候选账，不进行2440秒比较。

end 后的终账编码、写盘/fsync/readback、metadata复核、完整证据复查和 driver lease 释放计入单独 live tail；最后不递归写一份计时回执。只有私有 Completion 的 declared_driver_call_window_complete 为 true。imports/caller/return/process exit、持久化 tail 重建及 worker granular phase/observer separation 仍未闭合，不能称完整 program 生命周期或正式分项预算。

独立 pre-seal 审查发现并关闭 F1（close/terminal 后完整 Job/parent 晚漂移）、F2（保留文件identity替换 clock 小时目录）、F3（嵌套 metadata grammar/逐stage算术未严格复算）。新增有界 parent events/anchor/child reference、clock及全部Job的目录identity、文件stamp/hash和lock identity视图，包围最终科学复核、close、terminal确认与driver lease释放；held lock不读锁中字节。fresh metadata reader检查exact schema/false authority、同源head/bridge链，从完整stage向量调用已有account重算，并绑定最终anchor；不冒称重新执行了science或重建live authority。全部后置失败保留原parent outcome，无Completion、无retry。

初版根验证5 passed/5.38s、1 passed/74.12s、5 passed/357.00s；修订后三项受影响验证3 passed/215.28s，相关精确算术回归18 passed/2.13s，均exit0。最终独立只读R3完整13 passed/573.10s/exit0；按测试路径静态计数8个受控短synthetic Jobs，零真实native。最终三文件pins前后一致，无开放pre-seal finding，终态无相关进程。不是official verdict或运行许可。

新增metadata条件逻辑界为(2H+3)*524288+1 bytes、2H+4 files、1 root directory；H=192为202899457 bytes/388 files，排除controller子树、scratch、FS分配和内存。每hour live headroom合并该保守metadata界、当前Job、parent update、剩余clock records和scratch；没有资源预留或全任务准入。多次全树hash和保留有界视图的时间/内存成本须另行纳入资源合同。

开发检查 results/tables/rq2_h1_lifecycle_driver_v1_non_authoritative/development_checks.json，SHA256 e300a101fc841c1c5ca1f2b05cadc21e9e6e574b070a9c014f842303de735bee，绑定401pins。前序380pins、v2/v3 outer的895/1695成员及run的248/251文件fresh核验无漂移；初版及审查前后快照全部保留。完整192-hour实际链、producer/native coverage、完整phase/observer/分项预算、全资源准入、正式结果和新native授权均未取得；相应全局flags保持false。

下一步推进实际任务manifest及causal-key复用DAG，区分数值计算、来源与资源身份，并核对已有CFE必要条件诊断到已批准v2义务目录的证明绑定；不重做CFE映射，不把旧候选诊断直接作为v2排除证书。共同Rref/A、同合同完整LB/UB、完整资源合同、successor封存及全新official独立审查仍待完成。新具体native运行必须另获明确授权；整体目标继续进行中。


### 2026-10-05：v2 CFE 整 cell 解析排除 overlay 开发复审闭合

新增 experiments/rq2_v2_cfe_exclusion_development_v1.py、tests/test_rq2_v2_cfe_exclusion_development_v1.py、docs/model_spec/rq2_v2_cfe_exclusion_development_v1.md。根代理唯一写入，零 solver/native；复用既有 exact CFE preallocation，不改 src、已批准 v2 科学合同或旧封存结果。此为 R3 DRAFT/PRE_SEAL 开发证据，不是 official verdict、容量证书或运行许可。

固定 training witness：power start=192、outage seed=20260822，workload start=408，enrollment offset=162，原始 source hours=354/570。两份完整168h source windows及全部workload投影通过已有 pinned loader/projection；保留完整来源receipt、选定原行和精确有理数。package完整性读取包含holdout文件，但证明仅使用training rows，不以holdout结果选证据。w=407772206073/500000000000，R=118547425354783/5000000000000000。

并列保留已批准 q_eff>tau && q_eff>f*w，以及更强充分反例 q_eff>f*w+2*tau。后者来自局部放松 served_C<=f*w+tau、q_eff-served_C<=tau；不替换合同或认证现有runtime float bridge。若完整支持策略成功，就必须在具名pair该小时履约；若此前N/Rref/状态链失败或未决，它本身也不是完整支持UB。此反证不主张已构造可达N/Rref/A轨迹。对CFE-only、joint-correct及B6的CFE规划账适用，network-only无结论。

最终保留300个(alpha,f)算术组及全部1900完整theta/alpha身份；1856 cells有该强反例，44保持unknown。最小正relaxed gap为197389855855280462600947/25000000000000000000000000。解析依赖覆盖training LB 81537792、training UB 8235316992个义务身份；其中直接witness为LB 5568、UB 562368，其余pair仅依赖parent cell proof，不逐pair宣称失败。条件B6actual 27179264、holdout 79822848个身份记training UB前提不成立/未执行，不标不可行或实际失败。LB没有D轴；完整D网格、全部pair与原身份保留，omitted=0。仍待处理身份LB 29756608、UB 3005417408、B6actual 644336、holdout 29130752；这些不是必要求解次数或实测资源节省。

独立首审发现F1：单一conditional disposition可能误覆盖network-only holdout。已改为cell及coverage均按family/arm显式记录：holdout四臂中network-only全部unknown；B6actual仅joint-B6；44未知cells全部条件评价仍unknown。测试逐臂验证并核对数量守恒。初版报告、pre-review/post-review快照及首审finding全部保留。

根首轮18 passed/67.89s，相关CFE/projection/旧support/catalog回归77 passed/0.87s；首轮独立18 passed/64.94s，修订根18 passed/73.03s，最终独立18 passed/58.95s，均exit0。命令使用指定compute Python -B与-m pytest -q -p no:cacheprovider。初版及最终报告均audit后fresh inspect完整重建一致；最终候选三pins前后一致，无开放pre-seal finding，无残留相关Python/native进程。

最终报告 results/tables/rq2_v2_cfe_exclusion_v1_non_authoritative/cell_exclusion_audit_v2_final.json，4019867 bytes，SHA256 2e8c9f07db03426c02f3c38f5f938231cb6ca47f30537ad0d740ed9e22341e7c，绑定1711 source pins。开发检查 results/tables/rq2_v2_cfe_exclusion_v1_non_authoritative/development_checks.json，SHA256 39bbb8ba1e0d5c9337bafbec275da83aba99450358c41f900ef35f8ee02bb27a，绑定419 pins。前序401开发pins、v2/v3 outer895/1695成员、run248/251文件及字节数fresh核验无漂移。

后续须把该解析依赖绑定到实际任务manifest，完善合法causal-key复用DAG、共同Rref/A、剩余cell的同合同offline LB与完整policy UB，并完成192-hour/232-stage生产覆盖、计时与全资源准入、successor封存及全新official独立审查。complete_executable_task_inventory、causal_reuse_DAG_verified、operational_projection_bridge_verified、producer_coverage_proven、native_export_coverage、collector_integrated、component_budget_verified、resource_admission、formal_execution_ready、formal_result均保持false。新的具体native运行另需明确授权；整体目标继续进行中。


### 2026-10-05：v2 proof-aware obligation manifest 开发复审闭合

新增 experiments/rq2_v2_obligation_manifest_development_v1.py、tests/test_rq2_v2_obligation_manifest_development_v1.py、docs/model_spec/rq2_v2_obligation_manifest_development_v1.md。根代理唯一写入，零solver/native。基于固定catalog及上轮source-bound exclusion报告fresh inspect，编译前后重验全部1711 source views；自身实现也绑定并复查。四类目录全部身份可按family/ordinal按需查询，不物化数十亿记录；这仍不是complete executable task inventory。

resolve/encode_coordinate按原axis_order构成mixed-radix双向映射，严格拒bool/float/负数/越界及错轴。新义务identity绑定catalog SHA、family、ordinal、axis_order与完整coordinate。每次由完整theta+alpha重算cell SHA；直接witness比较完整power/workload window canonical bytes。UB的D=0/1身份不同但可关联同一D无关解析证明；LB/B6actual/holdout不新增D轴。ordinal、pair、split和proof disposition均为controller/audit记账，不进入policy输入。

逻辑DAG含8020节点：contract/catalog/source witness、一个exclusion overlay根、300算术组、292正反例组、1856 cell bindings及5568 arm-cell implications。边仅proof_reference/logical_implication，solver_reuse_edge=false；各node的solver_task_id、causal_key、runtime_request全部null。四类terminal disposition明确区分具名直接witness、同cell其他pair依赖parent proof、条件评价前提不成立/未执行、未取得证书。network-only及44未知cells继续unknown，B6actual仅joint-B6，holdout无默认D、UB或失败状态。义务总量与原四family目录一致，未删pair、未减资源预留。

独立首审F1发现unknown terminal只依赖catalog，无法单独绑定absence-of-proof scope；已令所有terminal依赖catalog与包含report/protocol/catalog/implementation pins的overlay，affected另依赖arm implication。反事实report pin改变时unknown terminal node ID改变，而义务identity保持不变；公开build拒绝该反事实无效pin。F2发现dataclasses.replace可保留token制造raw/cache不一致；已改受控public构造、只保留immutable bytes/tuples，拒绝direct constructor、replace、copy/deepcopy及pickle，原始bytes须fresh inspect重建。private compiler helper不是验证API。初版manifest、快照及findings全部保留。

根初版24 passed/113.17s，相邻exclusion/catalog回归45 passed/96.25s；独立初版24 passed/118.93s。修订根完整33 passed/143.22s；独立定向11 passed、22 deselected/29.76s，覆盖F1/F2、8020拓扑及快照无别名，未重复未改项。均exit0，使用指定compute Python -B -m pytest -q -p no:cacheprovider。初版和最终manifest均fresh inspect完整重建一致；三候选pins前后稳定，无开放pre-seal finding，无残留相关Python/native进程。不是official verdict或运行许可。

最终manifest results/tables/rq2_v2_obligation_manifest_v1_non_authoritative/obligation_manifest_v2_final.json，9219017 bytes，SHA256 befcfab8180a0124f15ad7652b085514c7aec6278e2b9d967e9885fc5a65fdd7。开发检查 results/tables/rq2_v2_obligation_manifest_v1_non_authoritative/development_checks.json，SHA256 fadec65f40904ed4a7a2ec484767a3bd6d14b6e4a5e9ab759d47fd798a72f246，绑定437 pins。前序419pins、v2/v3 outer895/1695成员、run248/251文件及字节数fresh核验无漂移。16MiB manifest cap和新增实际文件仅是本地开发边界，不是完整磁盘/内存/wall准入。

下一单元转实际causal-key/runtime任务绑定：复用已有H1 source packet、完整before/carry、role/resource身份及parent机制，区分数值键、来源身份与证据归属，不再扩展泛用graph/manifest层。共同Rref/A、剩余同合同offline LB/完整policy UB、192-hour/232-stage生产覆盖、计时与全资源门、successor封存及全新official独立审查仍开放。complete_executable_task_inventory、causal_request_keys_materialized、causal_reuse_DAG_verified、producer_coverage_proven、native_export_coverage、collector_integrated、component_budget_verified、resource_admission、formal_execution_ready、formal_result、native_execution_authorized均保持false。新的具体native运行须在包与门禁就绪后另获明确授权；整体目标继续进行中。

### 2026-10-05：v2 obligation → pending normal 输入绑定开发复审闭合

新增 experiments/rq2_v2_normal_obligation_binding_development_v1.py、tests/test_rq2_v2_normal_obligation_binding_development_v1.py、docs/model_spec/rq2_v2_normal_obligation_binding_development_v1.md。根代理唯一写入；复用现有 immutable obligation Resolver、H1 source parent、PendingWorkerInput 和 v3 request_key，未修改 src 或封存合同。仅接受 enrollment 0..167 的 unresolved training-UB obligation；四臂角色明确，已解析排除的 cell 拒绝，LB/actual/holdout/follow-up 不由此入口处理。

完整168-hour边际窗口校验包括catalog chain、CFE domain及250MW/12-place workload projection；仅当前hour独立校验RTS对应。whole_enrollment_marginal_domains_and_workload_projection_checked=true；whole_enrollment_RTS_correspondence_checked=false、future_dispatch_mapping_checked=false。完整坐标、原始来源时钟/展示时钟/相对模型时钟、parent/anchor/head/receipt、before/spec/limits及proposed Job budget分别绑定；不将记账标签传给policy。坐标或预算单独变化会改变binding ID，相同N数值输入仍复用原request_key。相同key不授予跨任务结果复用权。

独立首审F1收窄过宽全窗口表述；T1严格核对原request_key；T2分别验证坐标与budget变化。首次测试1 failed/22 passed/278.02s exit1是测试把receipt内部source pin自洽误当来源认证：保留实现，改为伪造receipt可自洽构造但原external receipt SHA拒绝；真实来源由fresh parent pending_input、外部receipt pin及独立current source重建认证。失败记录及修订前后快照保留。

修订根全量24 passed/314.56s；相关旧source/parent回归51 passed/95.85s；独立只读定向4 passed、20 deselected/289.61s，均exit0，指定compute Python -B -m pytest -q -p no:cacheprovider。三候选pins稳定，无开放pre-seal finding。零solver/native、零worker/Job，终态无相关进程。仅开发审查，非official verdict或运行许可。

固定真实来源样例：power raw192/workload raw408、seed20260822，模型hour0。results/tables/rq2_v2_normal_obligation_binding_v1_non_authoritative/binding_v1_final.json 为8052 bytes，SHA256 9f756d724a305ff2039d85157eb89ce28e1322a45f7b7fa5db861122b83e1849。N request key为85b7f386f7ec4aadb01b1c9c3e1f66024d052056b8f86bdb6c996a8bfe3b57cb。写后fresh inspect一致；父级关闭后的独立新Python进程按保存context重建仍一致。样例parent为pending_unknown，未产生accepted scientific carry，不可视为续跑许可。

开发检查 results/tables/rq2_v2_normal_obligation_binding_v1_non_authoritative/development_checks.json，SHA256 2ff5646b492c17becdb685c01ee49d03ccd81251b483921bae57da661a10a84e，471 pins。前序437 pins、v2/v3 outer895/1695成员、run248/251文件及字节数重验无漂移。新增样例/副本仍须纳入后继资源预算；128KiB局部record cap不等于资源准入。

下一步直接推进真实runtime交接和common Rref/A各自状态链，验证later-hour accepted carry与phase需求，完善完整任务及合法复用DAG、同合同LB/完整policy UB；避免再扩展泛用metadata层。live_parent_state_at_use_verified、writer_lease_authenticated、complete_executable_task_inventory、causal_reuse_DAG_verified、common_Rref_A_verified、producer_coverage_proven、native_export_coverage、collector_integrated、component_budget_verified、resource_admission、formal_execution_ready、formal_result均为false。仍需完整资源准入、successor封存及全新official独立审查；新的具体native运行另需明确授权。整体目标继续进行中。

### 2026-10-05：obligation controller 实际 release gate 与历史回放开发复审闭合

新增 experiments/rq2_v2_normal_obligation_controller_development_v1.py、tests/test_rq2_v2_normal_obligation_controller_development_v1.py、docs/model_spec/rq2_v2_normal_obligation_controller_development_v1.md。根代理唯一写入，旧src/worker/parent/clock及所有封存字节未改。constructor固定同一个training-UB obligation、168小时enrollment和exact Job budget；新增outer guard顺序在clock/controller/parent之前，独立obligation目录与lease不改变旧clock严格目录。

完整边际窗口预验证在旧_headroom hook内、clock/source intent之前完成。_job在live guards/leases内调用已有binder，核对typed pending输入，并预计算旧worker exact request SHA。旧controller在suspended child release前动态调用_check时，必须复核obligation bytes及已写request完整pin；同长改写并恢复mtime亦拒绝。worker schema与N数值输入保持原样，worker_obligation_authenticated=false。新controller header、每hour binding/job-link/terminal构成链；terminal确认及final check后才产生不可copy/replace/pickle的last_obligation_observation，入口及任何失败清空。

历史reader从完整source-parent prefix的_child取得经来源/carry重建的packet，独立重建历史obligation记录，核验exact Job、clock、outcome/anchor和三记录链；不对已消费pending调用旧binder，不重建live release授权。Windows持有中的一字节lease仅核验stat identity/size，避免读锁字节。成功前写job-link失败保留worker结果、parent pending；terminal写前/写后确认失败可留accepted parent，但无successor completion且禁止重试。新增逻辑存档界为(3H+1)*128KiB+1 bytes、3H+2 files，组合headroom纳入新增记录；不是完整磁盘/内存/wall准入。terminal写入仍在旧bridge interval之外，逐hour重复full-window/closure扫描成本尚未优化或准入。

首轮guard 1 passed/12 deselected/31.29s。首轮四项3 passed/1 failed/9 deselected/417.63s：真实三种release gate通过，合成两hour已完成但reader的fresh manifest重建被synthetic一小时source fixture拦截；已将已fresh验证Resolver明确接入test-only synthetic seam，保留失败记录与快照。独立F1锁字节、F2固定episode预算、F3公开typed成功receipt均修复；F4依赖闭包疑点经parent MEMBERS递归核查撤销，只读counterfactual确认base controller读取内容变化会改变新identity，不需重复改代码。

根最终全量14 passed/833.16s，6个短synthetic Jobs、0 real native；旧bridge三项回归3 passed/14 deselected/3.37s。独立定向2 passed/12 deselected/388.91s，2个短synthetic Jobs、0 real native。均exit0，使用指定compute Python -B -m pytest -q -p no:cacheprovider。真实来源测试以fake suspended child截住release，未启动真实worker；synthetic两hour测试明确使用source/catalog seam和保存raw，不是real RTS later-hour科学见证。覆盖request/binding漂移、固定坐标/预算、四个publication失败窗口、live-owner历史回放、重签previous/joblink/clock/outcome、错外部pin、缺失/额外文件及guard。最终三候选pins稳定，无开放pre-seal finding，相关进程为空。不是official verdict或运行许可。

开发检查 results/tables/rq2_v2_normal_obligation_controller_v1_non_authoritative/development_checks.json，SHA256 bb7882c34a9157402594be2107a20a2c71f09d3c54179124d8550e0a47e6cd12，491 pins。前序471pins及v2/v3 outer895/1695成员、run248/251文件和字节数均重验无漂移；初始失败、pre/post-review快照及counterfactual记录全部保留。

后续优先接入共同Rref/A各自state chain及已有业务小时事务，明确normal输出到同合同reference/actual输入的边界，补完整192小时phase/producer覆盖和实际任务/合法复用DAG、同合同LB/UB与全资源计时准入。新controller与完整生命周期driver尚须有意整合，不能把其继承bridge等同于完整lifecycle证明。real_RTS_accepted_carry_verified、full_enrollment_execution_verified、runtime_task_inventory_complete、common_Rref_A_verified、causal_reuse_DAG_verified、complete_LB_UB_certificates、producer_coverage_proven、native_export_coverage、collector_integrated、component_budget_verified、resource_admission、formal_execution_ready、formal_result、native_execution_authorized均false。仍需successor封存、全新official独立审查和具体新native运行明确授权；总体目标继续进行中。


### 2026-10-05：H1 current-only 信息入口开发复审闭合

新增 experiments/h1_current_grid_information_development_v1.py、tests/test_h1_current_grid_information_development_v1.py、docs/model_spec/rq2_h1_current_information_development_v1.md。根代理唯一写入，旧src及全部冻结产物保持原样。旧grid_information把完整未来forecast/normal schedule纳入pre_episode allowed_plan身份，旧carry要求该身份不变，不能直接承载批准的滚动H1合同。本单元仅复用纯静态network结构，不构造旧plan/current-information类型。

prepare(root, external header/terminal pins, completed_hours)重验完整obligation/source/carry/Job/clock prefix，从fresh accepted child重建最后一小时N；校验阶段数、projection身份、request/before/network/locks及N边界，返回前再次重验。decision view仅含中性relative hour、静态network、当期base/bounds/DC limits与前后normal commitment/当期generation。source clocks、完整carry、solver/run身份和canonical locks只在audit envelope中。该对象仅fresh-at-return，detached_consumer_authenticated=false；后继public physical kernel必须在同一owned调用中以root和外部pins重新prepare、消费并在返回前重验，或另立持久receipt/reader，不能凭exact type接受detached对象。

初版集成因old.json模块引用失败，1 failed/4 deselected/122.45s，首版纯4 passed/2.25s；旧接口相关5 passed/72 deselected/2.72s。全部失败记录和pre-review snapshot保留。独立F1已改显式json导入；F2新增非零workload .1/.2映射25/50MW、当期敏感性与未来行/审计clock不变性；F3在代码flags和spec明确认证边界。根最终6 passed/152.71s exit0，独立5 passed/1 deselected/2.65s exit0；指定compute Python -B -m pytest -q -p no:cacheprovider。完整测试含一个saved-report synthetic Windows Job，零真实native；不是real RTS accepted-carry科学见证。独立PRE_SEAL审查无开放finding，非official verdict。

开发检查 results/tables/rq2_h1_current_information_v1_non_authoritative/development_checks.json，SHA256 93e284449074302322d540c119ce7bcec40304145b2f41cca33b86eb42c92dbe，513 pins。前序491pins及v2/v3 outer895/1695成员、运行248/251文件（20931567/20938085 bytes）重验无漂移；最终无相关Python/Gurobi进程。初版失败、pre/post-review快照及独立记录均保留。

下一步进入H1物理protocol/carry/kernel及reference/actual各自selector和状态链，保持N→Rref→业务/A mapping→actual→paired commit顺序，明确当期outage disclosure与独立历史；不能把当前信息入口当共同前缀发布或Rref/A执行完成。公共冲突registry、完整192小时phase/producer覆盖、实际任务和合法复用DAG、同合同LB/UB、全资源计时、successor封存、全新official独立审查及具体新native授权仍待完成。detached_consumer_authenticated、common_prefix_publication_verified、reference_or_actual_ready、real_RTS_accepted_carry_verified、producer_coverage_proven、native_export_coverage、collector_integrated、component_budget_verified、resource_admission、formal_execution_ready、formal_result、native_execution_authorized均false。总体目标继续进行中。


### 2026-10-05：H1物理候选kernel开发复审闭合

新增 experiments/h1_current_grid_step_development_v1.py、tests/test_h1_current_grid_step_development_v1.py、docs/model_spec/rq2_h1_current_grid_step_development_v1.md。旧current_grid_step数学主体与exact residual机械移植到新H1类型，旧src/封存字节不改。保留全部DC balance、AC/DC bounds与flow、normal response、committable own-history ramp、startup/shutdown allowance、forced-trip down-ramp例外、explicit repair return cap及1e-6验收门；不修改normal reserve/dwell合同。

候选carry逐步绑定完整N boundary（network/completed hour/全部UID commitment+generation+age/evidence role），不沿用旧constant allowed_plan_identity；current decision identity可随hour变化。frame同时绑定packet的normal network pin；Rref与四个公开A arm严格隔离，own generation/disclosure/predecessor独立于N。新接口relative hour为0..191，旧disclosure只在内部使用boundary0与current h+1映射。origin必须显式提供incoming outage；可用机组取N声明初值、不可用取0，静态验收失败即拒绝，不提供替代初值。

本单元仅提供detached development数学入口和candidate carry。_frame只接受合成或上层已验证packet，不验证normal lex/native/共同发布；物理可行assignment不选择g、不认证Rref/A committed state或不可行性。后继operational owner必须从持久history与外部pins重建双方状态、在同一owned调用中fresh消费和返回前重验，不能把此detached candidate当认证凭据。

首轮kernel23 passed/11.35s，旧物理全量+H1信息纯相关46 passed/1 deselected/8.56s，均exit0。独立F1发现双N boundary可以同换foreign network，已新增normal_network_identity并补反例；F2发现expected SHA可被自定义相等对象绕过，已加exact built-in lowerhex SHA gate并覆盖custom-equal/bool/int/uppercase/长度，同时收紧lane字段类型；F3补完整build数学主体AST等价测试，覆盖未逐个实例化的fixed/curtailable/disabled分支。exact-residual AST也相同，10个数值case逐项比较完整变量域/bounds/fixed、线性系数/约束bounds/objective及assignment残差和next-carry数值。

修后根合并77 passed/1 deselected/18.35s，独立kernel31 passed/11.85s，均exit0，指定compute Python -B -m pytest -q -p no:cacheprovider；零solver、零Job。三小时own-generation反例、trip/continuation/repair、planned shutdown、full N boundary splice、cross-lane、clock及mid-audit drift覆盖。合成N frame只用于物理数学连续性，不声称normal可达/可行或real RTS accepted carry。独立PRE_SEAL无开放finding，非official verdict；当前无相关进程。

开发检查 results/tables/rq2_h1_current_grid_step_v1_non_authoritative/development_checks.json，SHA256 a22fc23c37f956ffce9e2d528126be3c990622e66b3db4f0cd66f444929b2c1f，533 pins。前序513pins、v2/v3 outer895/1695成员、run248/251文件及20931567/20938085 bytes均重验无漂移。pre/post-review snapshots、初版通过记录及全部findings保留。

下一步在此kernel上实现H1 reference LP/selector与actual selector，保持各自旧数值门和canonical locks；随后接共同同key冲突发布、persistent lane owner及业务/actual原子提交，不能把纯kernel通过当完整statechain完成。完整192小时phase/producer覆盖、合法复用DAG与全任务manifest、同合同LB/UB、完整资源计时准入、successor封存、全新official review及具体新native运行授权仍开放。detached_consumer_authenticated、normal_selection_authenticated、common_publication_verified、reference_or_actual_ready、persistent_lane_owner_implemented、real_RTS_accepted_carry_verified、producer_coverage_proven、native_export_coverage、collector_integrated、component_budget_verified、resource_admission、formal_execution_ready、formal_result、native_execution_authorized均false。总体目标继续进行中。


### 2026-10-05：H1 reference/actual阶段与saved-record回放开发复审闭合

新增 experiments/h1_selector_replay_development_v1.py、tests/test_h1_selector_replay_development_v1.py、docs/model_spec/rq2_h1_selector_replay_development_v1.md。根代理唯一写入，旧src、v2/v3封存与运行产物保持。reference LP采用P_ref∈[0,B]及(B-P_ref,L1,全部sorted UID generation)；actual固定外部exact power，采用(L1,全部UID generation)。复用旧Spec参数grammar和grid_evidence_replay独立重建能力，不能复用旧fixed-plan policy身份。

每stage exact envelope绑定input/policy/implementation、lane/power、spec/limits、model structure、index/label/purpose、完整前级frozen及float.hex与canonical objective hex。内部固定builder逐级fresh重建，native-shaped metadata/full assignment/canonical objective/residual经旧_replay复核后，再执行物理和rational selector lock/deviation审计。后续锁仅取diagnostic.recomputed_objective。完整reference n+2级、actual n+1级才出nonpublished numerical candidate；前缀、timeout、infeasible/feasible-only、任何数值失败均无candidate，失败record后仍附suffix直接拒绝。没有native执行入口，不产生执行认证或g的共同发布。

保留旧数值门原样：非负有限LB/UB/objective、LB<=objective、UB-LB>=0、abs(UB-objective)<=min(feasibility_tolerance,1e-9)、原absolute/relative gap和strict lock参数。独立设计说明中的精确objective<=UB要求经来源核对撤回，未额外收紧或放宽合同。typed ReplayLimits同时约束声明的per-solve秒数、threads、完整call count及count*time总秒数；仅证明声明自洽，不认证实际历史执行资源，也不把旧short20stage绝对cap当完整UID支持上限。

独立F1确认根自查：raw report SHA会污染后继计算键，现selection identity只含input/policy/canonical locks/公开carry/request，raw SHA留审计；两个合法不同AC/DC循环flow witness给出同一candidate及下一小时key。F2禁止失败后suffix；F3补声明budget门；F4使用批准范围内feasibility=1e-6并先确认raw valid/optimal，证明5e-7反例确由1e-9 strict selector lock拒绝。E1新增committable/fixed/curtailable/disabled混合UID每级完整变量/线性rows/objective等价；E2补末级carry-generation不一致拒绝。

初版29 passed/125.68s。修后定向16 passed/1 failed/22 deselected/64.85s：唯一失败是混合4UID的旧actual oracle fixture仍声明2stage，已改为其实际5stage预算，未改实现门限；失败与中间快照保留。根最终合并75 passed/1 deselected/182.19s，独立定向14 passed/25 deselected/58.52s，均exit0。随后仅强化Fraction纯测试，用B=.3、P=.1要求精确1/5且不同于先浮点减法所得值；根1 passed/38 deselected/2.47s、独立1 passed/38 deselected/2.35s覆盖最终test字节，code/spec未变。指定compute Python -B -m pytest -q -p no:cacheprovider；全程零真实native、零Job。fake solver-shaped records仅测试自洽回放，不证明实际最优/真实执行。PRE_SEAL无开放finding，非official verdict；终态无相关进程。

开发检查 results/tables/rq2_h1_selector_replay_v1_non_authoritative/development_checks.json，SHA256 28f842ce44c6c36ad45f92ad92f95f86a6152f061e9716c6356323be5d167967，701 pins；包含最终fresh import的197个repo依赖和前序533pins。前序证据及v2/v3 outer895/1695成员、run248/251文件与20931567/20938085 bytes均重验无漂移。各轮测试、初版/修订/纯oracle强化前及最终快照、findings和两次import closure完整保留。

下一步把科学projection与独立run witness接入same-key冲突发布、persistent lane owner和业务/actual原子事务，同时建立H1 reference/actual的真实raw ingress/Job/计时与全UID资源包；已有zero-face数学优化待H1专门适配，仅在认证accepted native prefix和exact L1=0后使用。source/normal/native认证、detached consumer、common publication、reference_or_actual_ready、persistent_lane_owner_implemented、producer_coverage_proven、native_export_coverage、collector_integrated、component_budget_verified、resource_admission、formal_execution_ready、formal_result、native_execution_authorized保持false。完整192小时phase覆盖、合法复用DAG/任务manifest、同合同LB/UB、successor封存、全新official独立审查和具体新native运行授权仍开放；总体目标继续进行中。


### 2026-10-08：H1 outage 来源适配开发审查闭合；完整支持左边界仍阻塞

环境恢复：exec_command 可用；初始 git status 852条，未发现Python/Gurobi进程。原outage草稿6704 bytes已fresh readback，test原不存在。根代理唯一写入，保留全部未提交文件、冻结协议、旧结果与失败记录。

新增 tests/test_h1_outage_source_development_v1.py、docs/model_spec/rq2_h1_outage_source_development_v1.md、experiments/audit_h1_outage_boundary_development_v1.py；既有 experiments/h1_outage_source_development_v1.py 草稿本轮未改字节。适配器从pinned同split/seed/chain读取raw_start-1与当前prefix，boundary0/current1..192；入窗持续事故onset=None；拒绝缺行/隐藏替换/ID复现，显式generator repair cap。source ID/clock仅审计，prepare前后重读。返回的Prefix可构造，仅fresh-at-return，不是认证凭据。

根outage32 passed/1.65s；相关source_window/event_disclosure/H1 physical85 passed/25.22s；独立合并117 passed/21.97s，均exit0，指定compute Python -B -m pytest -q -p no:cacheprovider。独立boundary JSON重建一致。零solver/native、零Job。PRE_SEAL在detached adapter范围无开放实现finding，不是official verdict。五个待审文件前后hash稳定。开发检查 results/tables/rq2_h1_outage_source_v1_non_authoritative/development_checks.json，SHA256 179480df368ea468e4c69be908e77ddbb6d29b842726991d6dd8115deefb77f0，714 pins。前序701pins与v2/v3 outer895/1695成员、run248/251文件及20931567/20938085 bytes无漂移。初次冻结复核记录器因v2缺top-level files发生KeyError，已按实际members重验并在frozen_recheck保留说明，未改旧产物。

完整catalog来源边界审计保留全部义务：holdout512条中3条缺前置行，training_lb/training_ub/training_b6_actual各523条中3条缺前置行；共6个独立窗口、12个family实例。training seeds20260822/23/24的raw_start=0缺hour-1；holdout对应raw_start4440/4560/4632缺4439/4559/4631。boundary_coverage.json SHA256 a1d5bcafde41ed9bf9a3d3c4d46ebaf6bd0a57641837d3937e9dda18e31a3dc8。obligations_removed=0，full_boundary_coverage_verified=false。不得删掉窗口、用当前行代前置状态、跨split借行或查询未来event结局补初态。完整执行依赖的初态来源仍input unresolved；解除需明确科学决定及versioned predecessor/origin输入依据，再全catalog复核unresolved=0且删除义务数=0。

另两项后继门保持开放：多小时offline Prefix没有owned current-hour进度绑定，不得把完整steps/audit.rows传给hour-local policy，必须按已提交进度逐小时消费；repair cap仅外部机制输入，来源及持久绑定尚未注册（下游kernel现有nameplate gate已核验）。N source correspondence、persistent lane owner、same-key registry、paired commit、H1真实raw ingress/Job/分项计时、完整192小时phase/producer、合法复用DAG/任务manifest、完整同合同LB/UB与资源准入仍未完成。resource_admission、formal_execution_ready、formal_result、native_execution_authorized保持false。v3单次native授权已消费，本轮未执行新native。总体目标未完成；依赖缺失初态的正式接线和运行暂停，待科学输入问题解除后继续，仍需successor封存、全新official独立审查及具体新native另行明确授权。
