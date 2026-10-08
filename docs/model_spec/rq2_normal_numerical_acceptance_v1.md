# Normal 数值验收 successor v1

## 范围和授权

2026-09-28 用户明确批准 `rq2_normal_numerical_acceptance_candidate_v1.md` 中的数值修复，
回复“同意该数值验收修复，继续推进（推荐）”。本组件将该决定应用于已保留的 H25 原生诊断，
并重建完整 canonical assignment 与连续时序 witness。它关闭的是该归档的数值 normal
验收问题；不替代完整正式实验 runner、四臂服务合同、全支持计算或 training/holdout 证书。

`src/solvers/rq2_normal_numerical_acceptance_v1.py` 是有前置条件的计算组件，调用者必须先
验证归档 schema、输入与执行来源。`experiments/verify_rq2_h25_normal_acceptance_v1.py`
是本次唯一受审的来源绑定入口：固定五个旧归档 hash，检查完整 manifest、source request、
runner/collector/adapter 身份，再调用 fresh canonical 和 chronology 核验。
不能将其内部 assessment 函数当成任意外部数据的认证入口。

## 冻结验收矩阵

1. 原生 `ObjBound`、`ObjVal`、`ObjBoundC` 与原始 assignment 不修改；native lower ≤ upper。
2. native/Pyomo 上下界逐 hex 一致；native/canonical 目标代数一致，引用赋值逐 hex 一致。
3. 原生 OPTIMAL、Pyomo ok/optimal、solution optimal；线性 minimization MIP 范围。
4. canonical/ObjVal 差绝对值 ≤ 1e-9；完整 canonical 残差（含变量界）及整数误差 ≤ 1e-9。
5. raw gap `(ObjVal-ObjBound)/abs(ObjVal)` ≤ 1e-8，按 binary64 值转精确分数比较。
   双零值 gap=0 是已授权约定，非 Gurobi MIPGap 属性逐字复现；其它零目标情形 unresolved。
6. fresh 连续时序 witness 无错误且 terminal carry 非空。旧 witness 的 1e-6 内部限不变；
   前置完整 canonical 1e-9 验证仍必需，不能以 witness 较宽阈值覆盖它。
7. source request 及既有执行 archive pin 全匹配；结束前复核来源、文件身份和实现 hash。
8. verifier 的五个 solver 入口运行时禁止，异常与成功均恢复；verifier 自身 solver calls=0。
9. `numerical_solver_optimality_accepted` 只在上述条件全部满足时成立。
   exact、security、native execution authentication、whole-task resources、formal result 均 false。
10. 外层显式保留 mechanism initial state、非观测 power mapping、未注册 coupling；真实观测仅为
    已归档的原生通道与公开来源数据，不将机制初态或映射变成实测值。

## 验证与信任边界

窄测试覆盖真实 2 小时小型 MIP、source/结构/赋值/残差/runner 反例、chronology failure、
五个归档文件篡改、manifest inventory、五个 solver guard、finally restoration 及 helper drift。
候选谓词另有 29 项边界和反例；旧 normal 相关回归保持通过。准确运行结果写入独立 closure。

真实 H25 首份开发 assessment 保留为 `assessment.json`，SHA
`073124431891f519ae09bc7301004f867c518707355ba5e51c3e2111ee1a0433`；其依赖清单尚未包含
replay helper，属被后续 preseal assessment 取代的开发记录，不是 seal evidence。
最终 seal 只绑定完成依赖 pin 和来源角色补强后的 `assessment_preseal.json`。

fresh replay 使用共享模型、残差和代数 kernel，是独立执行，不是独立实现 oracle。
原生与 canonical 完整约束矩阵不作精确等价证明，信任已固定的 Pyomo→Gurobi translator。
已有 Job observation 作为被 hash 固定的历史记录读取，不能重新证明历史 OS 执行真实性，
也不能把一次 H25 的结果推广成其它窗口的数值或资源证明。

生产 outer 原子发布包含 `SEALED_READY_FOR_INDEPENDENT_REVIEW` 才构成 seal；之前均为 draft。
之后由新实例只读 reviewer 对 exact outer 审查。official PASS 仅关闭本组件 review gate。
此只读组件无运行 lease，不创建 formal-run authority；完整实验门仍由 blocker register 约束。
