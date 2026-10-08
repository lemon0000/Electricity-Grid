# 连续网侧请求的信息合同与实现前置

日期：2026-09-16。状态：DRAFT_NONAUTHORITATIVE_CONTRACT。
本文件整理下一接口的依赖与验收，不注册请求算法、科学参数或正式运行合同。

## 为什么这是下一项

`outage_trajectory.py`及其短求解使用完整未来事故路径；`business_grid.py`及其短求解接受完整已提交
业务轨迹。它们可以提供离线物理见证，但没有定义仅使用当时信息的网侧请求。
`capacity_policy.py`按当前请求执行；`continuous_planner.py`和`planner_short_solve.py`仅提供
offline、continuous-recovery relaxation的开放前缀证据。因此，当前没有完整的
“网侧揭示 → 请求 → 固定业务动作 → 实际网络状态”因果链。

现有模块继续复用。不能把offline最优削减向量改名为causal grid request，也不能将前缀容量区间
重标为完整服务或因果策略证书。离线训练选容量本身不等于未来信息泄漏，但其选择规则、训练支持、
固定执行合同与holdout隔离必须显式绑定；当前区间不证明该固定策略可履约。

## 每小时的信息与状态

| 对象 | 接口需保存的内容 | 仍需确定的科学语义 |
|---|---|---|
| normal plan | 唯一计划身份、发布时点、计划所用信息、当前小时计划状态 | 计划是否可预知后续负荷/可再生；不得暗含未来事故 |
| prior actual state | 上小时实际发电、availability、正常计划dwell与实际状态的区分、绝对来源小时 | 初态来源、修复后回接与跨窗口交接合同 |
| current observation | 当前负荷/可再生/拓扑、已揭示故障和修复状态、来源与split | 故障/修复在动作前或动作后揭示；未来repair是否已公布 |
| grid request | 数值、MW基准、适用义务、生成规则与原观测身份 | grid-only义务、净POI减载或其他对象；不得自动视为可加分量 |
| business response | 原请求、已执行grid/CFE响应、恢复、实际功率、shortfall及cohort状态 | 同一减载的CFE co-benefit是否允许；恢复受网侧限制时如何处置 |
| current dispatch | 当前小时的完整网络赋值及独立残差见证，角色为derived mechanism assignment而非真实观测 | 调度目标、非唯一解选择规则、响应与修复限额 |
| next state | 从已验当前赋值提取的实际末态、与前态/请求/动作共同绑定 | 无见证时保持unresolved，不能消费未经验证的后缀 |

以上未确定项没有默认值；不能从已有测试fixture的参数推导正式注册值。
生产者不得只删除完整events参数而仍通过输入对象、normal plan或缓存读取未来事件。
多个同小时子步骤必须共用同一个来源小时，避免请求、业务响应和网侧验收重复计入风险分母。

## 实现与验收顺序

1. 列出既有normal计划、实际carry与事件来源能提供的揭示证据，区分观测值、benchmark派生值和机制声明。
2. 将上述未决语义形成自包含的可审阅合同，包括动作先后与失败处理；再实现对应DRAFT单步请求生成。
3. 复用现有网络方程、预算、native证据与fresh赋值审计；仅向单步核提供允许读取的当前信息和已验证前态。
4. 用两条前缀相同、未来故障/修复不同的合成路径验证截至当前的请求与状态完全相同；normal计划的信息集也必须相同。
5. 验证跨chunk与整段推进一致、trip/repair边界、非零actual carry、响应后恢复负荷、无解/timeout与来源gap。
6. 再绑定训练容量、固定策略和正式输入闭包；完整服务容量仍另外需要continuation/closure见证。

前缀不变性是因果性的必要验收，不能只对常数输出或空接口测试后宣称因果调度已完成。
单步DC赋值仍不代表全N-1/AC安全认证；请求缺失、接口错误、数值失败、物理见证不足必须分别保留。

## 当前证据

只读领域核查与本页复核确认上述依赖关系，限定范围无实质问题；未运行solver或生成正式输入。
固定业务动作短求解的实现与验证见`rq2_business_grid_short_solve_v1.md`；它仍属offline证据。
科学选择与正式验收总表继续以`docs/plan/RQ2_连续正式实验决策与验收_v1.md`及blocker register为准。

## 逐小时来源核对与事件接口进展

| 现有入口/字段 | 实际证据含义 | 因果输入处置 |
|---|---|---|
| `simulate_n_minus_one_events` | seeded derived benchmark；event ID包含seed | raw ID/seed留在审计侧，不传给动作策略 |
| `end_hour_exclusive=min(...,horizon)` | 末端可被截断，未必发生repair | 无后续明确当前报告时保持down，不推导末端repair |
| 源起点stationary-down事件 | 原表start=0表示生成边界处已down | 当前揭示记录onset未知，不伪造边界trip |
| `run_short_grid_candidate`的normal builder | 构模不读events，仍使用全时段load/renewable与原输入身份 | event-blind不等于完整因果：normal计划的预测信息与发布时点仍待合同 |
| `ContinuousGridCandidate.hours/event_identity` | 包含完整原事件与整段摘要 | 不作为逐小时策略可见对象直接传入 |

新增`event_disclosure.py`将“当前动作前揭示完整N-1 outage overlay”作为显式机制，而非自动采用的正式协议。
普通完整当前报告驱动local ordinal、初态未知onset、ongoing、repair及不同组件边界转换；不生成网侧请求。
具体来源边界、实现与验证见`rq2_event_disclosure_v1.md`。真实来源适配、normal信息边界与request规则仍待完成。

正常计划信息投影后续已由`grid_information.py`开发，见`rq2_grid_information_v1.md`：原input/assignment身份仅在审计侧，
allowed plan identity从声明事前已知的信息重算，当前条件独立输入；36项新测试/179项相关回归及限定pre-seal通过。
它只实现信息隔离，不证明计划确实提前发布或赋值选择未看未来；完整因果链、request及dispatch仍待完成。

当前小时固定业务功率网络验收后续已开发为`current_grid_step.py`，见`rq2_current_grid_step_v1.md`。
actual carry从完整canonical及exact审计通过的赋值产生；41项新测试、173项相关回归通过，限定pre-seal finding已闭合。
该接口未选择dispatch，当前信息隔离不证明调用方的赋值选择过程具有因果性。下一项为owned短求解，之后仍需请求和选择规则合同。

## 2026-09-19 请求标量不能代替实际功率验收

已用当前模型和解析赋值验证一个机制反例：单机normal计划20 MW，prior actual=25 MW，双向ramp=10 MW/h，
当前外部总负荷0，DC baseline=20 MW。DC实际功率20 MW及发电20 MW可行；若进一步削减到DC=10 MW，
系统平衡要求发电10 MW，下降15 MW违反ramp 5 MW。当前exact审计分别返回残差0和5 MW。
这一核对仅构模及审计，不运行solver，不是经验事故或真实业务观测。

因此，即使标量网络调用G已足额响应，额外CFE减载或恢复动作也不能免除当小时实际网络审计。
固定commitment与prior actual下，可行DC功率不保证向0闭合；仅根据最大可供功率生成减载下界不足以刻画完整可行域。
请求设计须同时说明共同参考请求与各臂实际carry的关系、功率下界及恢复上界、CFE-only义务适用性与失败后的未知后缀。
这些是新机制设计的必要验收约束，不自动改变原加法合同、四臂estimand或旧冻结请求。

当前单小时owned短求解已开发为`current_grid_short_solve.py`，37项新测试/193项相关回归及限定pre-seal完成，
见`rq2_current_grid_short_solve_v1.md`。其目标为0，尚未选择用于固定策略的唯一dispatch规则。

下一实现候选已整理为`rq2_common_reference_request_design_v1.md`：四臂外独立reference生成共同raw请求，
各臂actual carry仅用于该臂物理验收；数值词典序选择与业务/网侧双提交单列。它仍是非注册设计，不能当作当前已运行策略。
