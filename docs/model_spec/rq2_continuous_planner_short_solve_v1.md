# Continuous planner短求解与原生结果证据

状态：`DRAFT_NONAUTHORITATIVE`。实现`planner_short_solve.py`，测试`test_rq2_continuous_planner_short_solve_v1.py`。
本入口执行一次开发求解，不运行正式实验、不发布生产结果或lease，不替代正式科学/数据/资源门。

## 入口与预算

`run_short_continuous_solve(inputs, arm, solver_specification=..., budget=...)`内部独占fresh canonical模型，
调用方不能注入模型、求解driver、status或bounds。复用既有solver_spec/create_solver/options和规模统计，旧冻结文件不修改。
budget要求显式purpose、time limit、threads、变量/约束数、scenario数和H上限；support/H及预测变量规模先于build检查，
实际规模在create_solver之前检查。每次最多一次solve，无重试或fallback。
此开发入口的适用性硬上限为30秒solver time limit、4线程、20000变量、100000约束、16个scenario、168h。
这些是短验证的资源门，不改变科学容量域或正式实验阈值；更大运行需其他明确验收流程。
数值适用性同时要求feasibility/optimality/integer tolerance均不超过1e-6；objective一致性使用
min(spec.feasibility_tolerance,1e-9)。这些上限由NUMERICAL_LIMITS捕获并进入result_id，旧solver组件及正式注册阈值不改。
time limit是solver选项，不是强制wall-clock终止保证，模型构建/加载/审计亦有开销。

## 独占流程与来源核对

1. fresh build，保存planner identity、全部未赋值Var快照及完整结构摘要。
2. 记录实际Pyomo/solver package版本，调用version-checked create_solver，核对返回options等于显式spec生成值。
3. 只调用一次`solve(load_solutions=False, options=...)`。
4. 要求原生Pyomo SolverResults，完整保存solver/problem/solution记录数和状态。solver与problem必须各恰一条；problem必须是minimize。
   SolverStatus/TerminationCondition/SolutionStatus保存类型、repr与枚举成员；每条problem保留sense、LB/UB的repr/hex及报告维数。
   不因ListContainer的默认首记录访问而忽略额外problem或solver；有歧义时仍保留全部这些记录并停止加载。
   problem报告目标数必须精确为1。变量/约束报告维数仅保留诊断：当前HiGHS原生接口实测这两项为NaN，不能用它们证明原模型规模。
   规模门使用内部canonical模型计数；所有原生变量仍须完整映射及一致。
5. 加载前核对结构与全部变量值未变。恰有1个solution才选择；0个或多个保留unresolved。
6. 显式解析每个原生变量标签及symbol map，拒绝未知/非变量标签、重复映射、缺少变量、非有限/缺失值。
   这是对legacy loader可能忽略未知symbol的额外防护。所有模型变量必须由该原生solution提供。
   solution若提供objective条目，其label须属于本模型目标且数值须与canonical目标在objective一致性门内吻合；原始条目进入result身份。
7. 使用select=0、ignore_invalid_labels=False加载，随后立即调用canonical assignment/exact witness审计。
   原生变量值必须逐项等于加载后的snapshot；结构、options和包版本再次核对。

加载异常不使用部分残留变量；错误记录阶段/类型/消息。无自动重试，不把异常、timeout、infeasible字符串或unbounded转换成不可行证书。
ShortSolveAudit只由内部求解流程构造，普通构造与dataclasses.replace均拒绝，以免修改已捕获运行事实。
result_id绑定捕获的runner CONTRACT版本、inputs/arm、budget/spec、版本、options、前后结构、初值/原生变量、状态/界、assignment身份和运行错误/耗时；evidence亦显式给出contract。
它是开发内容身份，不是签名或独立进程认证；该接口信任版本检查后的solver/plugin在同一进程内按API运行。

## 三类证据分别判断

- `relaxed_prefix_assignment_audited`：来源核对与完整canonical数值赋值通过。timeout若有唯一有效候选仍可满足该项；整体结果继续unresolved。
- `relaxed_prefix_interval`：还需原生SolverStatus.ok、optimal/globallyOptimal、唯一SolutionStatus.optimal、有限有序L/U、L不高于canonical objective、U与objective符合上述objective一致性门，且`(U-L)/max(abs(objective),1e-12)`满足显式relative gap。U必须位于声明capacity域[0,maximum_capacity]，L不得超过该上端；负L本身可以是合法松下界，不作静默clip。不得以abs修复倒置界，也不以optimal termination覆盖仅feasible/bestSoFar的solution元数据。
- `effective_prefix_witness_available`：已加载候选的独立精确动作见证通过；不要求其等于EDF量化因果策略。B6仍仅separate planning。

区间明确属于offline、continuous recovery relaxation的开放前缀对象，按声明的solver数值容差解释，并非有理数严格最优性证明。
松弛区间不以精确物理见证为必要条件：微量恢复可能通过前者而失败于后者。
`prefix_capacity_interval`、complete LB/UB、causal证书、infeasibility证书保持null，formal/security保持false。
没有continuation映射或完整履约见证时，不对完整对象给四臂归因。

## 开发验收

故障注入覆盖timeout有解/无解、多解、create/solve/load异常、预加载直接写值、结构/目标/options漂移、缺失/未知label、非有限数、界倒置/不符/缺失、非全局最优终止、预算前置拒绝。
真实HiGHS 1.15.1小例仅H=2、单线程、每次time limit=1s，四臂各调用一次；输入grid=(.25,0)、CFE=(.125,0)、eta=.8、首小时birth到期于第二小时。
最终72项targeted、9文件353项相关回归通过；独立方另复跑72项通过，限定范围无开放finding。
真实四臂小例原生容量依次.25/.125/.375/.25，数值及精确恢复见证通过。审查发现的metadata、contract身份、native inventory、数值适用性反例均已闭合。
源码SHA256：`566c05a85df84b7b33c1e8e60aa589aaf2f1760b16be8b0a3fc6a4651627ee23`；测试SHA256：`145ad7dbbce1cd5e18a1598908169bd7ecc8ffbfb09e8d1e54feb6040951b276`。
完整多日输入、正式规模、固定策略训练映射、风险合同及科学协议仍需后续验收。
