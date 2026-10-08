# RQ2 开发机任务与执行边界

更新日期：2026-09-28

## 当前主线快照（2026-09-28）

- 连续多日、恢复债务、四臂、拒绝后动作、前缀/组合诊断已有开发证据；不重复建设。
- 显式normal预算、来源worker及父控制器的短合成execute/audit链已通过限定pre-seal验证。
  最新入口为`docs/model_spec/rq2_scale_normal_controller_v1.md`：6项子进程/失败窗口及69项相关回归通过。
- 真实H25 normal仍为TIME_LIMIT可行解（gap约0.125%），未达到原最优性门；短合成成功不改变此状态。
- 任务清单缺口与3600秒限制已零solver核对，见`docs/model_spec/rq2_current_workload_inventory_v1.md`。
  15秒/级尚有非solver余量，23秒/级仅solver预留就超限；完整实验总量仍缺窗口/搜索/复用等声明。
  参数/窗口/评分建议已形成`rq2_continuous_science_candidate_v1.DRAFT.yaml`，尚未批准或完整注册。
  168h全支持直接逐级展开出现约1783亿次调用的条件规模；复用边界已有10项测试，见
  `rq2_computation_reuse_and_capacity_binding_v1.md`。reference理想共享仍不足以证明计算可行。
  完整目标与training/holdout证书合同、等价求解路线仍需设计；真实normal预算候选可独立准备。
- 正式continuous科学协议、20项实证未知/6项未注册选择、完整服务右删失验收及正式审查/运行门仍开放。
  本页后续按日期保留开发历史，其中早期“下一项”由本快照及末尾更新接续。

本页是当前工作导航，不是冻结配置、执行授权、结果凭证或论文证据。科学口径以
`agent.md`、`RQ2_公开数据鲁棒识别路线图_v6.md`和预注册配置为准；阶段门禁以
`docs/model_spec/blocker_register.md`为准。

## 1. 当前证据状态

- fresh HiGHS/Gurobi confirmatory pilot v4 已完成，四个独立 worker、结果重建和
  semantic contract 均通过；该结果只关闭跨求解器确认门。
- process-isolated HiGHS V8 已完成固定 `0008 -> 0009` nonformal evidence run，
  publication 为 `committed_success`，独立 post-result review 为 `PASS`。
- formal activation V6的official结论为`ESCALATE`；当前V7仅为无执行许可的
  `DRAFT_NONAUTHORITATIVE`，Windows验收矩阵与fresh PRE_SEAL review仍待闭合。当前没有
  可执行formal candidate或formal-run authority。
- 1071-block grid package、pairwise package和identification package均未发布。
- 四臂增强基线的 core、checkpoint contract、external preflight入口及
  identification/report contract已实现为 validate-only 状态；外部grid输入、
  独立复审、用户执行授权和正式结果门仍未打开。
- 联合服务可交付前沿科学v5、implementation v2与execution v3已分别取得其既定独立review PASS；
  但dispatched grid、Windows runtime replay和单独formal-run authority仍缺失，formal门未打开。
- 2026-09-12零solver审计发现v5的24小时完成期边界与末小时正CFE请求结构冲突；冻结541个
  training power blocks的hour 23正请求按alpha为`358/478/541/541`。逐时available-flexibility
  必要条件亦显示`alpha=0.85, flex_fraction=0.20`的18,394个raw pairs全部触发。raw grid/E0
  未知，以上不是正式46-cell物理结果。
- 用户已选择continuous multi-day state carry。当前新增内容仍为`DRAFT_NONAUTHORITATIVE`：保留
  hour 23义务，跨observation chunk携带完整事件/能量/恢复债务状态，并拒绝跨split/gap/
  trajectory/trace漂移；它不是完整formal planner或执行许可。
- 冻结margins的continuation availability/provenance审计已完成：power按split×seed有6条包内链，
  training/holdout block links为538/527；workload有2条包内链，各33个links。双边potential
  adjacency为17,754/17,391，但不是已注册coupling或同钟证据。dispatched grid、deadline、
  accounting/budget/recovery合同仍未绑定，`full_joint_service_continuation_ready=false`。
- 已有70-cell派生benchmark保持
  `R1=0, R2=0, R3=69, mixed=1, unresolved=0`，不支持原正向H2。

## 2. 本开发机可执行的工作

1. 维护研究问题、estimand、外推边界、blocker和论文叙事的一致性。
2. 对已存在的配置、manifest、checkpoint inventory和结果包进行只读核验。
3. 运行Ruff、单元测试、合成小例、`--validate-only`和零solver门禁测试。
4. 在明确开发授权下构建新的 non-authoritative draft，并完成pre-seal测试与
   fault injection；seal和独立review按`agent.md`第7节另行执行。
5. 完善四臂增强基线的测试、schema和报告模板，但不得把缺失的正式grid package
   替换为合成或历史checkpoint。
6. 按联合可交付前沿主线同步研究问题、estimand、论文叙事与证据门，同时保留
   `formal_result=false`与`security_certified=false`。
7. 当前开发环境的可用解释器为
   `D:\Miniconda3\envs\rq2-executor-v2-audit\python.exe`；旧文档中的
   `D:\conda_envs\rq2-executor-v2-audit\python.exe`在本机不存在。该路径差异只用于开发验证，
   不修改冻结执行链或替代locked Windows runtime证据。

## 3. 当前顺序

### 已有连续机制开发与当前短任务

2026-09-12至09-13已完成以下DRAFT开发，不再按缺失模块重复建设：

| 已有产物 | 证据入口与范围 |
|---|---|
| 公开数据统一交付 | `data/processed/rq2_public_data_delivery_v1_non_authoritative/`：12包、261字段、Google 744小时/31 raw-origin blocks；20项实证参数null、6项协议未注册 |
| 连续状态、服务平衡、恢复债务 | `multiday.py`、`debt_cohorts.py`：跨chunk守恒、到期短缺永久保留、unknown与截尾分开 |
| 四臂回放与固定因果策略 | `four_arm_replay.py`、`causal_policy.py`：显式动作/B6共享执行、首次拒绝保留原状态 |
| 前缀诊断包 | `rq2_continuous_prefix_diagnostics_v1_non_authoritative`：24组合、1038记录 |
| 拒绝后动作及固定补救 | `actual_actions.py`、`recovery_controller.py`：原physical/shared拒绝后同小时转共享机制，独立组合policy身份 |
| 组合诊断包 | `rq2_continuous_composite_diagnostics_v1_non_authoritative`：32组合、1330记录，1324验证、6未评价、114未提交输入 |

代码均在`src/rq2_joint_deliverability_boundary_v1/`。这些产物是合成机制开发证据，未形成正式最低柔性planner、
真实运行策略或经验风险。底层multiday已有非零aggregate carry-in小例，四臂/cohort/policy入口仍只支持显式零历史。

当前短任务已完成拒绝覆盖梳理及primary `policy_decision`停止分支的5项补充测试，见
`docs/model_spec/rq2_continuous_rejection_coverage_v1.md`。按用户指定顺序，B6 `separate_planning`拒绝后的实际动作合同
已形成独立DRAFT配置、实现和18项针对性测试，独立pre-seal审查完成，限定范围无阻塞实现finding。见`docs/model_spec/rq2_continuous_b6_planning_recovery_v1.md`。
新策略从同小时最后共享状态接续并保留原拒绝，以独立身份和唯一小时计数报告；旧trigger集合不变。
显式部分响应合同及接口见`docs/model_spec/rq2_continuous_partial_response_v1.md`：保留原请求，以执行量创建债务；
grid短缺candidate-only停止，CFE短缺与业务丢失分账。37项新测试及186项相关回归通过，独立pre-seal数值finding已闭合。
新增固定声明容量的连续策略与精确aggregate响应见`docs/model_spec/rq2_continuous_capacity_policy_v1.md`，
已纳入当前可用柔性、响应/ramp/min-event及剩余预算；51项针对性测试及248项相关回归通过，pre-seal findings已闭合。
容量诊断导出见`docs/model_spec/rq2_continuous_capacity_diagnostics_v1.md`；15项新测试与91项相关回归通过，pre-seal findings已闭合。
新non_authoritative包36组/1091条完整重放一致；下一项为同一策略/来源/会计期的已验证前缀状态交接。
该前缀交接薄层已完成，见`docs/model_spec/rq2_continuous_prefix_handoff_v1.md`：45项专项、195项相关回归通过，
独立pre-seal无开放finding并复核全部连续模型381项通过；可持久化机制非零状态，正式初态/period合同仍未注册。
连续四臂build-only规划内核见`docs/model_spec/rq2_continuous_planner_contract_v1.md`：58项专项、193项相关回归及
独立439项连续模型测试通过，限定pre-seal无开放finding；尚未调用solver或签发容量证书。
计划动作的独立逐时物理/cohort见证已实现，ramp系数finding已修复，41项针对性及234项相关回归通过，独立pre-seal限定范围无开放finding。
规格见`docs/model_spec/rq2_continuous_planner_witness_v1.md`。
solver赋值/残差/精确提取和raw outcome适配已实现，两项pre-seal finding已闭合，47项新测试及281项相关回归通过，独立复核限定范围无开放finding；
见`docs/model_spec/rq2_continuous_planner_assignment_v1.md`。
独占build→solve→snapshot已实现为短开发入口，规格见`docs/model_spec/rq2_continuous_planner_short_solve_v1.md`；
72项针对性、353项相关测试通过，独立pre-seal限定范围无开放finding。完整formal对象与runtime门不据此关闭。
下一项实现continuous normal网侧薄层：复用旧context/model、补显式初态residual dwell与末态carry，保留旧冻结字节。
来源错误仍需有效连续观测；真实continuous training容量证书与输入闭包、累计短缺/删失汇总及正式导出绑定仍需补齐。
永久业务放弃保持核心实验默认0，真实参数与正式数据门保持阻塞。

2026-09-16用户进一步指定先补缺项与拒绝动作语义；B6共享后继pre-seal审查已完成，显式部分响应已完成数值finding修复与复核。
正式实验仍需完整continuous科学协议和主容量合同，决策与验收入口为`docs/plan/RQ2_连续正式实验决策与验收_v1.md`。
旧grid是逐24h free-boundary SCUC，发布旧1071块不自动证明跨块机组连续性；continuous网侧输入还需后继合同与证据。
开放前缀容量UB不能作为完整恢复服务容量UB；未知未来/期限保留unresolved，完整主estimand不得偷换。
独立的机组跨chunk审计草案见`docs/model_spec/rq2_continuous_grid_carry_v1.md`，仅检查给定committable轨迹局部约束，
不是dispatch生成器或网络安全认证；其开发不选择待决业务参数。

### 正式科学与执行顺序（门禁保持）

1. 固定并独立复核当前46-cell/四臂零solver必要条件诊断；不按结果修改cells、support、容量或阈值。
2. 已完成冻结margins的continuation availability/provenance审计；其结论只覆盖包内邻接、排除区间与
   字段缺口，不把potential adjacency升级为joint coupling或完整业务continuation。
3. 新建完整versioned continuous科学协议，预先定义accounting periods、budget/reset、deadline、
   censoring、train/holdout estimand及additive/co-benefit边界。
4. 先由fresh独立R4 reviewer审查完整continuous科学协议及数据门；明确关闭科学finding后再进入实现。
5. 以跨边界duration/rest/event/energy/debt小例和数据门测试驱动正式planner实现。
6. planner implementation按`agent.md`风险路由另行接受独立review；不得复用科学协议review替代实现review。
7. 只有上述科学/数据/实现门关闭后，才继续V7 Windows验收、dispatched grid和另行授权的formal流程。
8. 完整grid与continuous support发布验签后，再开放pairwise replay、identification和bottleneck报告。

2026-09-16开发更新：continuous normal核心已新增（`rq2_continuous_grid_normal_v1.md`），覆盖H>24、初态残余dwell、
canonical全变量审计与开放末态carry；82项targeted及325项相关回归通过，独立pre-seal限定范围无开放finding。
现有RTS源25h构模成功但未求解。下一项是owned normal短执行产物与事故响应连接，完整continuous grid与formal门仍开放。

该连接器已进入DRAFT验证，见`rq2_continuous_grid_candidate_v1.md`：44项targeted、270项相关回归通过，
四个真实微型case验证完整normal基线、原事故时钟、20 MW正grid need及zero-DC确认；独立pre-seal限定范围无开放finding。
下一关键缺口为事故态跨小时调度/修复回接及完整输入发布，不能将当前逐小时corrective当作连续事故轨迹。

## 4. 停止条件

- timeout、missing incumbent、资源停止或证书不完整只进入`unresolved`。
- E0保留无条件质量，不进入条件业务风险或R3。
- 缺未来观察只将completion记为right-censored；缺注册deadline记为completion合同缺失。二者均不得
  清零carry state或抹去已观察到的服务/违规。
- 不以任意tail、silent zero obligations、跨split/gap拼接或无依据budget reset补齐连续轨迹。
- 未发布完整grid package前，不运行pairwise或identification。
- 未取得独立review与单独formal-run authority前，不启动、恢复或替换formal run。
- 不复用v5的202个HiGHS checkpoint或历史Gurobi的9个checkpoint形成新正式结论。

## 5. 入口

2026-09-16开发补充：多小时事故态`outage_trajectory.py`已有构模、27项解析/接口测试及限定独立预审，
相关四文件176项回归在最后两项测试加入前通过。它消费已审计normal候选，以显式机制origin和repair cap
连接实际发电；仍缺事故态结果见证、实际末态交接与owned求解入口。完整连续输入发布和正式运行边界不变。
最新规格为`docs/model_spec/rq2_outage_trajectory_v1.md`，执行次序以blocker及科研执行步骤末段为准。

后续已补`outage_assignment.py`与`rq2_outage_assignment_v1.md`：完整原赋值审计、同一problem/assignment
的actual末态提取及normal carry分列，33项新测试随五文件211项回归通过。独立预审的运行时合同漂移已修复并复核闭合，
独立33项通过；事故态owned求解、完整输入发布和formal门仍待完成。

事故态owned短求解现已由`outage_short_solve.py`补齐开发入口，40项新测试及六文件251项相关回归通过，
独立pre-seal40项通过。该入口只运行显式短预算的一次小型LP；weighted输出offline标量目标证据，fixed只输出可行见证。
规格见`rq2_outage_short_solve_v1.md`。业务实际功率与网侧连接、正式continuous包和formal门继续开放。

固定业务实际功率构模/赋值连接现已由`business_grid.py`补齐，37项新测试、六文件193项回归及独立37项均通过。
规格见`rq2_business_grid_v1.md`；只接受全已提交prefix和显式机制MW/来源配对，CFE短缺与网侧可行性分列。
下一项为固定动作的owned短可行性求解；正式输入及运行边界保持。

固定动作短求解现已有`business_grid_short_solve.py`与`rq2_business_grid_short_solve_v1.md`。
最终37项新测试、六文件236项回归通过，独立pre-seal的solver outcome finding已修复并复核闭合。
网络赋值通过仅作为离线物理见证，CFE短缺/完整恢复与因果输入仍单列；正式输入及启动边界不变。
下一项因果网侧请求的信息合同已整理为`rq2_causal_grid_request_contract_v1.md`，未代选科学语义或实现generator。

事件揭示子接口已开发为`event_disclosure.py`，见`rq2_event_disclosure_v1.md`；仅接受显式当前N-1
outage overlay报告，保留未知初态onset和未修复末态，不向策略暴露raw event ID/seed/未来end。
36项新测试随63项相关回归通过，独立pre-seal的state构造finding已修复并复核闭合，独立36项通过；normal计划信息集和request生成仍未闭合。

正常计划审计与当前输入隔离现已开发为`grid_information.py`，见`rq2_grid_information_v1.md`；36项新测试随179项相关回归通过，独立预审限定范围无开放finding。
raw source/seed留审计侧，当前条件独立于事前预测。normal选择/发布时间的真实证据及请求生成仍待完成。

当前小时固定功率网络验收已有`current_grid_step.py`，见`rq2_current_grid_step_v1.md`；41项新测试及173项相关回归通过，
独立pre-seal fixed机组边界finding修复闭合。actual carry只由合法完整赋值推进，仍无请求/调度选择或正式输入发布。
下一项为owned单小时短求解；机制输入、完整服务与formal边界保持。

上述短求解后续已开发为`current_grid_short_solve.py`，37项新测试/193项相关回归及限定pre-seal完成，见`rq2_current_grid_short_solve_v1.md`。
下一项是共同请求、各臂actual carry及dispatch选择设计，当前尚无正式continuous请求包或完整因果策略。

共同请求设计第一步已开发为`reference_grid.py`，44项targeted/193项相关回归及限定pre-seal闭合，见`rq2_reference_grid_v1.md`。
后续数值selector/所选reference状态已开发，验收记录见`rq2_reference_selector_v1.md`。
剩余依赖为各臂实际dispatch选择、共同请求适配及业务/网络双提交；不发布正式请求或改变旧四臂对象。

后续fixed-power actual dispatch selector已开发并完成限定pre-seal，46项targeted/220项相关回归通过，
见`rq2_actual_dispatch_selector_v1.md`。初态与跨小时policy身份、exact功率及全级失败不提交已有网侧基础；
下一项共同请求单位适配及业务/网络双提交，正式来源、完整恢复和运行规模仍待验收。

共同请求单位适配后续已开发，38项targeted/223项相关回归通过，独立pre-seal来源finding闭合，
见`rq2_common_request_adapter_v1.md`。G/U通过Fraction保真；审计侧source binding检查split/seed/hour。
下一项固定mapping和reference来源的业务/网络小时事务；正式输入包及运行条件仍未齐备。

- 科学路线：`docs/plan/RQ2_公开数据鲁棒识别路线图_v6.md`
- 冻结确认性主线：`docs/plan/RQ2_联合服务可交付前沿确认性方案_v5.md`
- 不可变科学基础：`docs/plan/RQ2_联合服务可交付前沿确认性方案_v1.md`
- 冻结指标规格：`docs/model_spec/rq2_joint_deliverability_estimands_v4.md`
- continuous边界草案：`docs/model_spec/rq2_joint_deliverability_boundary_successor_v1.md`
- continuous边界配置：`configs/rq2_joint_deliverability_boundary_successor_v1.DRAFT.yaml`
- 零solver诊断：`results/tables/rq2_joint_deliverability_boundary_diagnostic_v1_non_authoritative/`
- continuation审计规格：`docs/model_spec/rq2_joint_deliverability_continuation_availability_v1.md`
- continuation审计配置：`configs/rq2_joint_deliverability_continuation_audit_v1.DRAFT.yaml`
- continuation机器包：
  `results/tables/rq2_joint_deliverability_continuation_availability_v1_non_authoritative/`
- 论文导航：`docs/plan/RQ2_论文路线图.md`
- 阶段门禁：`docs/model_spec/blocker_register.md`
- 增强基线：`docs/plan/RQ2_增强基线鲁棒性预注册_v1.md`
- 历史Windows交接快照：`docs/plan/RQ2_执行机交接_v2.md`


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
