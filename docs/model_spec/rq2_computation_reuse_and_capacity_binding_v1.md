# 计算复用边界与训练证书绑定缺口

2026-09-28，DRAFT_NONAUTHORITATIVE。本次检查现有实现，不启用缓存、不改变task身份、预算或科学门。
定位代码均在`src/rq2_joint_deliverability_boundary_v1/`。

## 数值相同与证据可复用是两项要求

| 对象 | 已核依赖 | 当前可得结论 |
|---|---|---|
| normal数值输入 | 完整inputs含时间、网络、baseline、初态、carry、request | 只有完整输入相同才可讨论重复数学问题；单看source hour或负载均值不足 |
| normal来源记录 | `scale_normal_source.request_identity`同时绑定source request、pair/assembly pins、原始resource plan及budget | 数学输入相同不允许把已有source-bound record/receipt改挂到不同cell/task |
| reference数值选择 | `reference_grid`读取info/disclosure/before；不读取后续CFE/柔性业务字段 | 仅在该完整三元组逐字相同且selector/spec相同时，才是潜在相同数值问题；跨窗前史不同不能省略 |
| selector policy/record | `scale_selector.policy_identity`仅归零source_hour，保留task_id、role、resource合同、UID与caps | 同一task跨小时policy稳定，不意味着跨task、跨arm或改预算可复用归档 |
| CommonPublication | `scale_hourly_transaction.publish_common_record`另绑定source_hour、mapping/source_audit、limits、due、available | 同一reference记录可按不同业务观测重建不同publication；不能把整个旧publication作为新cell对象 |
| actual数值选择 | `prepare_arm`先用完整业务历史/债务和capacity得到动作，再绑定exact power及info/disclosure/before.grid | 单按当前功率或source hour缓存会漏前序电网状态；容量也可能改变动作/功率 |
| actual归档 | 另绑定selector/spec、role、task和budget | 即使完整物理数值问题相同，当前接口仍不许可跨任务重挂证据 |

业务历史不是actual网侧LP的隐式额外输入：它通过动作选择影响传入功率。若完整网侧输入、前序状态及功率
均相同，可以进一步研究数值复用；但仍需证明业务动作来源、各自cursor提交与证据归属，而不是共享业务状态。
本检查未证明任何跨cell缓存已经安全，更未改变一次性调用/unknown invocation规则。

## 针对性验证

新增`tests/test_rq2_computation_reuse_boundaries_v1.py`，复用原小例及archive/replay入口：

- 单个已归档reference分别改变CFE、due、available及limits，禁止再次调用solver；reference相同而publication身份不同。
- 原物理input identity保持不变，改变task/resource合同/规模caps后，新policy身份变化且原record被独立回放拒绝。
- actual:0与actual:1即使其余数值限制相同，policy身份仍不同。
- 同一初始网侧状态、同一publication，容量1.0与0.4产生不同实际功率及dispatch request。
- 同一请求功率与当前info，改变通过origin静态availability/commitment/上下界检查的机制初态，
  actual input identity变化；origin构造不提供完整网络平衡/潮流见证。

命令：compute Python `-B -m pytest -q -p no:cacheprovider tests/test_rq2_computation_reuse_boundaries_v1.py`，
10项通过（14.34秒）。真实求解仅既有小型reference fixture的一秒上限逐级调用；其余为纯准备/重放。
未修改被核实现、旧测试、预算、冻结配置或研究结果。

## 共享reference也不足以解决直接展开规模

上一候选共`14644+14336=28980`个pair。
计数来源为`results/tables/rq2_continuous_science_candidate_v1_non_authoritative/structure_audit.json`，
SHA256 `6ba0fc07cf551a9fc1d18952849b46e8e8ffb051dca8accb8da41e9b5c4ec884`。
条件计算仍假设每个pair-cell执行一次完整168h四臂episode，不计normal/搜索/审计：

- 原直接路径：`28980*168*46*(160+4*159)=178270122240`次selector级调用。
- 即使未来能证明每pair的reference跨46-cell只做一次：
  `28980*168*(160+46*4*159)=143215914240`次，减少`900/4577`，约19.7%。

这是假定共享成立后的算术，不是已实现优化、实际执行时长或任何算法下界。原始输入预验证拒绝可提前停止，
但不能把这种停止写成完整服务成功。仅建设reference缓存并不能让完整直接展开路线具备已验证的计算可行性。

下一步计算工作应先形成输入依赖DAG及每类任务的物理身份/来源身份/资源身份分界，再比较保持词典序、
逐级数值门与四臂公平性的等价求解路线。凡涉及去除UID级、改变目标、近似替代、支持选择或停止条件，都必须
单独证明或按科学变更审阅，不能为减调用量直接修改。

## 训练容量到holdout的绑定要求

当前`capacity_policy.from_config`明确要求`training_capacity_certificate is None`，策略证据类别只能是
`mechanism_assumption`；现有planner/selector返回也不提供完整容量证书。给`capacity_declaration_id`取一个
训练名称并不能完成证书绑定。策略policy_id可能跨split相同；训练/holdout来源和状态由各自cursor额外绑定。

后继绑定必须同时携带并核验以下对象，不能只增加一个SHA字段：

| 对象 | 必须一致的内容 | 不能接受的替代 |
|---|---|---|
| 目标合同 | 完整服务/前缀、arm规划账、cell参数、时间/period/债务与future合同 | 用prefix UB当complete UB，或把未定义目标标为已认证 |
| training证据 | 训练支持及权重身份、来源/初态/normal信息声明、完整求解与逐时见证、有效界/gap/残差 | 只有求解器status、单个代表点成功、缺完整支持验收 |
| 容量值 | 由预注册规则选定、确实处于相应证据范围且同单位的数值 | 任取LB、复制未接受incumbent或holdout后加容量 |
| 固定执行策略 | 完整policy参数/实现身份、capacity值和声明身份 | 只用容量相等替代策略相等，或让holdout重优化 |
| holdout来源 | 独立split/window/pair身份和独立初态 | 接入training末态、重选好窗口或删除未知质量 |
| B6区分 | separate planning容量与共享实际执行两种合同均具名 | 将分离规划的容量证明解释成共享执行履约证明 |
| 失败报告 | 明确已验证F、未评价U、无调用/未知调用及不可行证书分别记录 | 把数值未决当实际服务失败或数学不可行 |

完整科学目标仍未绑定，故本轮不实现一个默认接受机制容量的“训练证书适配器”。先明确上述证据接口和
目标合同，才能实现有意义的正例及错split、错cell、前缀冒充完整、B6语义混用等反例。

独立限定预审核对了上述测试、身份边界及19.7%条件算术；按反馈收窄了机制初态措辞并绑定计数来源。
未发现需要修改现有执行实现的实质finding；不据此授予复用权限、完整资源认证或formal-ready状态。

## 2026-09-28 完整词典序的零偏差后缀证明

独立只读领域审计确认了一条待实现的计算路线。当前 reference 目标依次为
`(B-reference_power, sum(d_g), generation_g 按完整 UID 顺序)`，actual 为
`(sum(d_g), generation_g 按完整 UID 顺序)`。每个 UID 都有 `d_g>=0` 及
`d_g>=generation_g-normal_plan_g`、`d_g>=normal_plan_g-generation_g`。
若已求得的完整当前模型 assignment 使 L1 目标精确为零，那么所有 `d_g=0`，
在固定零 L1 的 lex face 上所有 `generation_g=normal_plan_g`。故余下 UID 目标均为常数，
可逐级保留 label、顺序、lock 和目标值，以解析证据关闭后缀；不需要删除任何目标。

reference 的前两级仍正常取得证据，actual 的第一级仍正常取得证据。全部五角色条件命中时，
158 UID 的每小时实际native调用可从 `160+4*159=796` 降至 `2+4*1=6`；事前完整最坏预留
仍为796次。这只是条件调用数，尚无实际数据命中率或wall-time结论。
必须用精确数值表示检查零，不能以显示零或 `<=lock_tolerance` 代替。
物理 assignment 仍按浮点残差验收，因此结论是数值可行赋值上的解析 lex 最优，不是整个
MILP 的精确有理可行性证书。

完整零 solver 路线还需要来自相同当前模型的完整 flow/angle/generation 等赋值。现有
`SelectorRequest` 不携带这个 candidate，`CurrentGridInformation` 的 normal generation 向量
不足以证明当前 outage/ramp/actual power 可行，故不能直接跳过前级求解。

现有 `scale_selector.py` 对每个 label 无条件求解；`scale_selector_replay.py` 的归档回放要求
每级 raw.calls==1，尚未接纳解析证据。下一必要开发是 versioned successor 的混合证据链：
保留真实 native prefix，另设 `analytic_zero_face` suffix 及零 solver 重放，不伪造原
`GridSolveEvidence(calls=0, optimal=true)`。绑定同一 input/policy/hour/disclosure/before-state/
prescribed-power、完整 UID、模型结构和完整 assignment；各阶段仍保留 previous locks。

验收反例包括近零非零 L1、UID 缺失、其它功率/历史的 assignment、当前 outage/ramp 不可行、
reference request 为零但 L1 非零，以及未来将 flow/angle 加入目标或 carry。
任一前提不成立就不能解析关闭。该路线仍需实现、针对性测试、资源核算和独立审查，
不是已完成的计算门，也不缩减完整研究支持。

上述段落保留设计审计时点。后续已实现独立 development successor 的混合 native/analytic core
和零 solver replay，专门规格见 `rq2_selector_zero_face_v1.md`；21 UID 合成对照确认旧23次/新2次
求解且逐目标、request、carry一致。旧 `scale_selector` 和旧回放保持原样。
后续混合core与store/worker/controller/archive均已分别封存并通过official review。
小时事务、完整episode及顶层execute/audit监督也已接通，246成员outer
`configs/rq2_selector_zero_face_episode_v1.OUTER.SHA256SUMS.json`已封存并获得fresh official PASS。
一小时四臂合成机制包实际6次native调用、仍预留11次，独立audit新增solver0；完整服务及
资源认证保持false。仍未取得真实158UID命中率及全支持运行成本，完整计算门开放。
准确测试与审查状态见blocker register，不把设计证明或小例当成完整正式实验可运行证据。
