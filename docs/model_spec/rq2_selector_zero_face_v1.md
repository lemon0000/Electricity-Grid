# 完整 UID 词典序的零 L1 后缀

## 目的与边界

本 successor 为现有 reference/actual selector 增加解析后缀路径，保持全部 UID 目标及顺序。
`scale_selector_zero_face.select_hour` 负责真实 native prefix 与后缀选择；
`selector_zero_face.certify_suffix` 重建后缀模型、检查代数与物理赋值；
`scale_selector_zero_face_replay.replay` 不调用 solver，重新核验 native prefix 并生成解析后缀，
逐字节对照完整归档。旧 selector、record、worker、controller 和已冻结 normal 数值验收不修改。

当前是同步 development kernel，无进程资源监督、持久调用日志或正式运行权限。
现有 worker/store/controller 的 exact 类型仍拒绝新结果，接入需显式 successor，不能伪装旧类型。
本组件不能单独解除全支持计算门；尚无真实 158 UID 数据的命中率或 wall-time 证据。

## 数学与数值合同

reference 前级目标为 `(B-reference_power, sum(d_g))`，actual 前级为 `sum(d_g)`。
前级继续使用原 native `_solve` 与全部原数值门，不将 normal 的新数值验收规则扩展到 selector。
只有最后一个 native 前级被接受、L1 目标精确为零、完整赋值中每个 `d_g=0` 且
`generation_g=normal_plan_g` 精确成立，才尝试解析后缀。近零不是零。
不满足精确零条件则继续原 UID 求解；解析审核失败则保留已完成 prefix，返回 unresolved，
不产生 next state，不把失败当数学不可行。

对每个 fresh suffix model 检查：

1. UID inventory 与 network、normal plan、budget 完整一致。
2. deviation 的实际有效下界非负；两条约束的真实 linear repn 分别为
   `generation-plan-deviation <= 0` 和 `plan-generation-deviation <= 0`。
3. 前级锁定包含激活的 `sum(deviation)==0` 精确等式；不是容差带。
4. 唯一激活目标为 minimize 当前 UID generation，无其它目标项。
5. 完整变量赋值、fixed 值、canonical residual 和 integrality 通过原 specification 阈值，
   reference/actual 的独立 physical witness 无错；reference request lock 通过原 lock tolerance。

非负性与零和强制所有 deviation 为零，双侧约束继而固定所有 generation，故每个 UID 目标
在零 L1 face 上均为常数。这是实际模型行上的目标证明；完整物理可行性仍按浮点容差核验。
`objective_exact` 是该目标 binary64 值的精确分数；既有业务/physical witness 的 decimal-rational
口径继续保留。prefix 原值不改，后缀逐级保留 previous locks、label、objective hex、模型 hash。

## 证据与状态

原生前级保留原 `GridSolveEvidence`，没有创建 `calls=0, optimal=true` 的假 native 证据。
后缀使用独立 `AnalyticStage`，`evidence_kind=analytic_zero_face`，certificate solver calls=0。
每级绑定 input、policy、implementation、完整 UID 和 assignment identity；完整 assignment 与
physical witness 只存于最后一个解析阶段，避免每个 UID 重复保存大对象。
`analytic_lexicographic_objective_proved=true` 不代表完整有理可行性认证；
`rigorous_exact_physical_feasibility`、`formal_result`、`security_certified` 均 false。

policy identity 使用独立 namespace 并绑定新实现；source hour 保持 invocation binding，
跨小时 policy 不因此改变。来源、当前 disclosure、before state、实际功率均由原 input identity
约束。helper 与 owner 返回前重核来源/策略/实现，不跨臂、跨历史重挂证据。
预算仍预留完整最坏 UID 求解数，结果另记真实 native 调用数，不用条件节省冒充资源通过。

replay 只接受完整 selected chain，核对外部 hash、16 MiB 上限、实现依赖、每个真实 native
前级与 canonical 赋值，重做后缀证明，要求重新编码的结果与原字节完全相同。
未完成记录保留供诊断，不通过本回放输出状态。replay 是共享 kernel 的独立执行，
不是独立实现 oracle，也不重新认证历史 native OS 执行。

## 验收矩阵

- reference/actual 零偏差真实小例：分别 2/1 native calls，完整 UID stage 与物理 carry 保留。
- 非零 L1：继续完整 native 路径，native-only replay 通过。
- 21 UID 零偏差：原路径 23 次、新路径 2 次，逐目标 hex、共同 request、最终物理 carry 一致；
  21 个解析阶段全部零 solver 重放，赋值/witness 各仅保存一次。
- 近零非零 L1 不解析；native timeout 或缺变量不能进入后缀。
- domain、双侧行、零和等式、目标项、active/sense 等前提被破坏时拒绝。
- input/policy/budget/实际功率、完整赋值、构建中 policy drift 反例失败闭合。
- 解析证书篡改、native calls/purpose 与阶段顺序篡改即使重新计算外层 hash 也拒绝。
- 两小时 reference/actual state 与 policy 连续，旧模块相关回归、sealed normal hash 不变。
- 非零 reference request 配零 L1 仍可解析；20.1 非 dyadic 例核对 binary64 精确分数。

命令、实际测试数量、结果 hash 与 pre-seal/official 审查状态另记于 closure 和 blocker register，
不得以本验收矩阵文字代替已运行证据。
