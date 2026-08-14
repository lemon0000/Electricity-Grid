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
| RTS-GMLC 6小时selected-N-1 DC SCUC/ED | resolved for scoped public benchmark | `rts_gmlc_google_day0_first6h_selected_n1_dc_scuc_v1`完成2020-01-01 00:00-05:00 UTC六小时求解；每小时12个预注册状态含normal，2轮约束生成后全部状态复核；固定组合ED目标`157084.446540127 USD`，有效master下界`157084.446540126 USD`，认证absolute gap为`1e-9 USD`、relative gap为0；产物manifest SHA-256为`405c5109ef405f1961f6e9e461be5bfa42bd88f074bd30fa49e67006f6edcd10` | 仅该具名范围可置`chronological_dispatch_request_built=true`和`chronological_grid_dispatch_coupled=true`；初值为派生自由边界，事故表为空，`completed_periods`为空，且非实时、非完整N-1、非AC，`security_certified=false` |
| RTS-GMLC 24小时selected-N-1 DC SCUC/ED | resolved for scoped public benchmark | `rts_gmlc_google_day0_full24h_selected_n1_dc_scuc_v1`完成完整day-0 24小时求解；每小时12个预注册状态，关键支路`A12-1/B22/C6/CA-1`、关键机组`121_NUCLEAR_1/213_CC_3/313_CC_1`，3轮约束生成后全状态固定组合ED目标`1193156.5322057535 USD`，有效master下界`1193155.3829459916 USD`，absolute/relative gap为`1.1492597619 USD`/`9.632095e-7`，独立残差最大约`1.4835e-9`；产物manifest SHA-256为`61b9d8c127354375769b5c1cf9e45e4340eafb0e89d8b07acbd8a08c9e1a0399` | 只解除该具名公开软件benchmark的24小时计算规模门；不解除真实绝对MW、真实柔性/恢复、观测事故、full-N1、工程级AC或`security_certified`/正式VMA阻塞 |
| RTS-GMLC 六候选共同状态多POI比较 | resolved for scoped benchmark comparison | 机械候选`108/120/208/220/308/320`共同使用每小时24个selected状态；120/108/220/320可行，208/308在自由边界连续commitment LP前缀中model-infeasible；bus 120为唯一证书分离的最低成本可行候选；aggregate manifest为`85f157a5f14f73ffa851c8dc1bc263f67719d794a900101b987dcab3f21dac66` | bus 108是已见锚点，不能称六点全盲；模型不可行不是工程场址不可接入，最低DC成本也不是站址推荐 |
| RTS-GMLC 代表方案direct AC replay | resolved as amended diagnostic sensitivity; certification and treatment-followup gates failed | amendment-004批次完整报告2304 case，2296收敛、8不收敛、0 direct-secure；收敛case中V/Q/支路/P违规分别为2296/2217/717/1470；non-slack PG偏差为0，DC1残差不超过`3e-9 MW`；manifest为`ee4894bba4e65433ffed4b31e4d96c78035bd2413dd4fa6accb3eb9f16c0609a` | 只证明冻结的无补救direct PF未通过；已有零注入normal对照但不是逐case匹配因果对照，且无工程接入设备、真实Q/控制和full-N1，不能归因于POI或宣称工程不可行，`security_certified=false` |
| PYPOWER同址slack机组语义 | resolved by transparent amendment 003 | 首个完整批次因内部机组排序导致实际slack UID与报告UID不一致，父manifest `51ba90b...`已作废为诊断；003要求REF母线恰有一台在线committable机组并机械复现旧错误，corrected结果所有收敛case的non-slack PG偏差为0 | 父批次的全部outcome不得作为最终结论；固定`pypower==5.1.19`和`ENFORCE_Q_LIMS=0`，后续依赖升级必须重审语义 |
| PYPOWER同址Q控制初始化语义 | resolved by transparent amendment 004 | 发现同址在线Q-inert机组`VG`可覆盖唯一Q-capable控制器的源`VG`；004只允许把唯一Q-capable源`VG`复制到同址Q-inert行，并保持bus VM作为Newton初值 | amendment-003结果manifest `2b5b705d...`及`2276/2304`统计只作invalidated parent diagnostic；正式direct replay只使用004结果 |
| 零数据中心normal AC与共同恢复门 | method-blocked for treatment follow-up | direct control为24/24收敛、0/24 secure；560 reference/distributed为11/24和22/24，565为22/24，三组IPOPT原边界各22/24，均未见证h15/h21；`repair_005`已发布4/6 checkpoint，candidate 5在cost normalization中断，active lease为stale evidence但被保留，`operational_interruption` manifest为`66fd455aa958c06c809f9a51a5a9588a932843b83b2cd2953b9982bd1bdb057b`；当前无solver进程，历史attempt均不得恢复且不构成不可行证据 | `treatment_followup_gate_passed=false`；`repair_005_resume_allowed=false`，后续须新建attempt并重新取得lease；六个预算候选checkpoint、完整frontier、manifests、两阶段certificates、primary regret及final 24-state audit验证前，不得启动joint AC、依赖该对照的treatment或论文结果固定；另一解除路径是取得有来源的tap/shunt/补偿及控制参数 |
| V3两套relative-gap字段的解释 | resolved as authoritative-field separation | stage顶层按feasible incumbent归一的`target_attained/eligibility_status/maximum_acceptance`是唯一正式资格；嵌套certificate按`max(abs(LB),abs(UB),1)`归一的relative/target字段仅作通用辅助诊断 | 判断target是否达到时只读取stage顶层字段，不读取嵌套`certificate.target_gap_attained`；checkpoint仍须检查`certificate.valid`、maximum acceptance、final audit、primary regret和residual audit。论文不得引用嵌套target字段；未来后继schema应删除或显式重命名该冗余字段 |
| M6完整网络-业务时序闭环 | external-blocked after scoped 24-hour coupling | Google已形成744小时归一化形状、cell f/pdu17一天的同系统功率-NCU配对及24小时零柔性派生业务基准；原生RTS-GMLC已有完整day-0 24小时selected-N1 DC后端、amendment-004 direct AC和零注入恢复诊断 | 仍缺观测绝对MW、完整PDU工作负荷、真实柔性/恢复参数、同钟观测具名事故、full-N1和工程级AC参数/控制/恢复；零注入AC共同见证门也未通过，不得进入正式CFE/容量认证结论 |
| 真实重大停电事件分布 | processed candidate cohorts; independent-event calibration blocked | 已冻结1534源行、1521候选组及主/敏感性队列；主持续队列1385组/1398源行，重复组保留source IDs并以非缺失max/min而非求和审计 | 候选组不证明独立物理事故，仍不得估计事故频次或无条件时长分布；无资产ID、拓扑和SCUC，不得映射为RTS具名N-1或声称与业务同钟 |
| Google同系统工作负荷-功率配对 | resolved for one-PDU one-day normalized pairing | cell f/pdu17 day-0取得336格小时usage、1328条machine event和唯一audit；600秒偏移后形成24小时功率-NCU上下界、168行priority明细及可加载的零柔性`derived_benchmark`，全部SHA锁定 | 只解除“一PDU/一天/归一化功率/受限usage人口”和业务schema桥接缺口；不是绝对MW、完整PDU工作负荷、真实柔性或恢复证据 |
| ENTSO-E观测资产事故 | external-blocked on security token | 匿名API实测401，当前环境无令牌；页面批量导出同样要求登录 | 用户完成免费注册和REST API令牌申请前不执行；取得后仍不得把ENTSO资产ID映射为RTS ID |
| X只有MW上限 | mechanism-only | 新增连续轨迹包络，硬检查响应、持续时间、休息、事件数、MWh、债务、恢复功率和期末债务 | 合成参数不能解除合同认证阻塞 |
| T指标依赖声明的静态24小时 | resolved as evidence separation | 静态M3的连续验证小时改为0；另以8784小时时间轴输出显式压力轨迹里程碑 | 正式逐时运行T仍受时序电网和业务数据阻塞 |
| 50% Pmax响应与机组事故频率安全 | external-blocked | 继续标记合成灵敏度，机组持续事故不冒充响应前频率状态 | 不能签发运行安全或响应认证 |
| branch 10非计划孤岛 | external-blocked | 排除并作为失败单列；数学多岛平衡不视为处置证据 | 正式N-1认证受阻 |
| 扩建缺少AC工程参数 | external-blocked | 只报告DC MW机制结果 | 不能进行扩建AC认证或把MW增量写成MVA |
| 固定在线机组、无逐时新能源与跨时约束 | external-blocked on RTS-24 mapping | RTS-24仍只使用8784小时时间轴和Area 1负荷代理；独立原生RTS-GMLC已完成24小时benchmark | 原生24小时结果不能回填机组集合不同的RTS-24，也不能据此声称RTS-24逐时SCUC、可再生联合安全或运行认证 |
| 真实业务恢复轨迹与恢复头寸缺失 | external-blocked | Google现有同系统day-0配对仍只有priority和NCU usage，没有可恢复比例、checkpoint、真实恢复headroom/效率/功率或合同deadline；Alibaba也不提供这些字段 | 只能把低优先级或作业类型标为柔性候选并做预注册敏感性；不能签发持续容量、恢复或正式T指标认证 |
| Word研究方案中文编码损坏 | external-blocked on clean source or approved reconstruction | Git初始提交与当前DOCX均已把大量UTF-8中文误存为乱码并含不可逆`U+FFFD`；无干净历史版本，未用Markdown覆盖原19张表和格式 | 当前以可读Markdown执行计划和模型规格为准；论文冻结前需取得干净源文件，或经确认后从现有可读文档重建DOCX |

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

首批公开生产数据已于2026-07-16取得并完成分源处理。Google PowerData 2019的55个可连接PDU经`bad_measurement_data`过滤后形成744小时形状；40,896个domain-hour完整，每小时有54或55个域，跨域只作无容量权重均值/中位数而不求和或插补。全窗峰值归一化只允许固定回放，不能跨train/holdout使用。Alibaba `stage1_core`全表审计覆盖1,055,501个job、1,261,050个task、1,055,032个group-tag和1,897台machine；主正GPU请求队列为732,318个task/714,903个job，缺失`plan_gpu`的223,965行保留为空且不填零。两个源的处理产物均使用稳定gzip/CSV和SHA清单。

Google受限配对查询已在项目`exalted-summer-490612-m6`完成。三次成功Job processed合计551,002,439,062 bytes、billed合计551,004,667,904 bytes，低于1 TiB门限；两个失败Job均未报告processed/billed字节。质量审计折叠1109个完全重复组，并对98个CPU冲突键保留上下界；233,888个多priority组进入`ambiguous`，963,596个无先验priority组使用显式`synthesized`标记。PowerData以`time-600000000`对齐，day-0的288个`production_power_util`样本全部质量不合格，因此只使用`measured_power_util`。

本地处理得到24行同系统小时配对和168行priority明细；CPU-time总下/上界为65,620,667.38184452/65,620,667.50039005 NCU-s，低优先级候选份额的小时边界范围为0.2860至0.4288。机器事件按ADD/REMOVE/UPDATE左闭状态重建，后续UPDATE不向前填补；`hour_index=18/19`共保留44.908767 unknown-capacity machine-seconds。该人口仍按`alloc_collection_id IS NULL OR 0`抽取且`population_is_complete_pdu_workload=false`，绝对PDU容量仍隐藏，priority候选不等于可削减或可恢复业务。Alibaba没有连续功率、checkpoint、deadline或恢复参数，且与Google没有可对齐真实日历；不得把两者拼成观测配对数据。ENTSO-E观测事故仍需令牌，RTS-GMLC故障率抽样只属`sampled_from_published_rate`；所以完整M6阻塞和全部正式认证字段保持不变。

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
