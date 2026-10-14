# H1 exact operational business adapter 开发单元

DRAFT_NONAUTHORITATIVE。R3；根代理唯一 writer。此单元实现 detached current business 数学适配，
复用旧 `capacity_policy_bidirectional` 主体；不是 source owner、共同发布、actual paired commit 或正式结果。
旧 src、冻结参数、活动阈值、约束和12位恢复量化保持原字节。

## 输入与表示

`Mechanism` 固定 alpha、f、rho 和250MW单位。`current` 接收当前 workload、原始 alpha=1 CFE source
fraction、Rref grid_request_mw 和 relative hour，全部数值明确为 Fraction。grid_request_mw 表示
`B-P_ref`，不是 P_ref；除以250后进入旧业务请求。当前 preallocation 内部重算，未接受 caller提供的
effective request/surplus。此处机制域允许小型声明案例，不认证19 theta/1900 cell注册或训练容量。

原始CFE、effective CFE、y、surplus均完整保留。对raw component与raw combined不一致先拒绝。
正Rref normalized request≤exact 1e-6时按既有mapping门拒绝，不能截断。
还检查旧 `_effective_call` 分别使用 Fraction zero 和 float zero 的真实运算路径；若binary/exact
分类不同，入口保持 unresolved，不能默默更改旧阈值。这没有新增 epsilon 或近似接受区。

旧 ContinuationHour/HourlyLimits 的 Real 字段以 Fraction进入；CFE循环小数surplus不转float。
旧 BidirectionalObservation.available_flexibility 是strict built-in字段，f*w必须能用整数或
满足 `Fraction(str(float(q)))==q` 的decimal语义表示，否则拒绝且不推进。保留原exact inputs
和旧observation中的转换后字段，转换可重算。该规则不声称binary float与有理数完全相同。

limits 为 available=f*w、headroom=rho*(1-w)、CFE surplus=allocation.surplus、call_limit=1、
maximum_recovery_power=1；D、eta、event/debt/energy/ramp等沿用输入的固定旧 policy/envelope。
旧主体负责 `q+r<=D`、grid优先的aggregate response、EDF与recovery floor12位。

## 相对时钟与状态

`initialize_development` 只接受 power/workload clock都为0的明确 compatibility anchor。
action t=0..191对应business hour=t+1；此anchor不是一条真实raw前驱观测。
source labels、split、seed、provenance仍在旧cursor审计中，但不进入科学投影。
有效当前义务的due为business hour+24，否则None。168小时后的新请求照常执行，birth/debt保留；
`phase`是派生审计属性，不额外传给旧policy。停止与登记评分由后继owner实现，本单元不递归延长窗口。

`BusinessCarry`保留完整旧cursor和完整ExactCurrent历史。每次prepare检查其旧记录的deterministic
replay、对应exact observation、固定mechanism和连续时钟。它不是外部认证凭据；后继owner必须从
持久且外部pinned prefix恢复，不接受手工构造对象取得执行资格。

科学payload包含固定policy数值/规则、mechanism、完整current历史、全部action/shortfall/status、
initial和current physical business state、envelope、ledger全部cohort及deadline历史。
capacity_declaration_id与accounting_period_id的任意标签仅留audit，科学投影保留D与nonrolling期规则。
不删除事件状态、累计预算、observed violations、None或已知deadline miss。
B6在本单元仅为shared actual business execution；其两个planning账及其LB/UB证据仍在外层接线。

`prepare_development`输出business candidate。业务拒绝时next_candidate与actual_power均None；
成功时exact检查 `P_actual=(w-grid_served-cfe_served+recovery)*250` 与q+r<=D。
即使业务成功也不能据此持久提交：必须先得到同lane actual接受，再由outer transaction成对发布。
来源绑定、Rref witness认证、paired commit、resource admission与formal均未由本单元证明。

## 验收范围

四臂原主体重放等价；1/21 exact surplus与原12位恢复；label变化的相同科学历史与不同audit；
strict scalar无损/有损边界；exact阈值、两侧rational、float相邻值与float-zero混算；raw/effective
mismatch；192小时连续推进、168/169 birth与192/193 due、末债与None；错误key/progress/mechanism/
历史、业务拒绝不推进、copy/pickle隔离。全部使用zero-solver机制案例，不证明真实source支撑或调度可达。
