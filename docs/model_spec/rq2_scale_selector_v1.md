# 完整UID规模selector数值内核

状态：DRAFT_NONAUTHORITATIVE。实现`scale_selector.py`，保留旧reference/actual selector、预算、结果及所有已绑定源码。仅进行合成例验证，未运行H25 selector或episode。

## 独立入口与复用

`ScaleSelectorBudget`独立于旧`GridDevelopmentBudget`；`budget_for_hour`重新检查完整资源声明，从指定episode、source hour和reference/actual角色派生完整阶段数、各阶段秒数、线程与模型规模上限。资源报告及`execution_resource_contract.py`、`execution_workload.py`源码摘要共同绑定资源身份。声明一致不等于真实资源验证或执行授权。

`select_hour`保留reference的request→L1→全部UID和actual的L1→全部UID。复用旧`_stage_model`、`_audit_stage`、原生`_solve`，不删阶段、不合并目标、不改变锁定和容差。实际UID必须与预算逐项一致；当前小时必须与预算source_hour一致。这里source_hour是`CurrentGridConditions.source_hour`，不能把数据文件的0起始行号直接当作运行小时。

求解前构造最大阶段模型，核对真实变量/约束上限；每阶段保留原生状态、LB/UB、gap、canonical赋值、物理见证、偏差与目标锁定审计。缺界、超时、赋值/锁定失败会停止后续阶段，不能给出下一状态。

## 身份与连续状态

调用者提供外部input/policy pin；policy绑定新内核、旧selector依赖、资源派生源码、solver specification、完整任务/角色/UID和预算。source_hour属于单次调用绑定，计算固定policy时将该字段归零，使同一任务相同选择规则可跨小时保持policy；实际调用仍逐次检查原source_hour，返回结果保存原预算。

新`ScaleSelectionResult`与旧selector结果类型不同。阶段审计对象沿用旧类型，physical carry也沿用旧状态结构，但policy身份不同；不能将新结果冒充旧episode接受的结果。actual origin由新初始化入口产生，保留原物理初态审计。`actual:0..3`标签只绑定预算/政策，不证明输入业务状态属于对应臂；后继episode wrapper必须用arm cursor/spec检查规范四臂映射。

资源清单中的normal input pin与当前信息视图的来源连接仍需上游核验。本内核不接收完整prepared normal及其最优性证书，不能自行确认normal已被接受、预测信息正确或缓存复用合法；不能以合成测试的可行normal代替真实链所需的最优normal。

## 失败与资源边界

原生pipeline返回完整raw后，调用数按raw保留。pipeline抛异常或中断、返回非法调用证据时，总`solver_calls=null`，并保留已经完成部分的`completed_solver_calls`和stages；不推断当前阶段零调用。审计或最终状态构造失败保留已返回raw、全部已有阶段及已知调用数，返回unresolved且无next_state。即使所有stage accepted，finalization失败也不能视为整次选择成功。

这是同步数值内核；`durable_invocation_tracking=false`、`hard_resource_limits_enforced=false`。它没有持久intent、wall/commit硬终止、进程静默证明或文件归档保障；进程被杀时仍需外部监督器保留unknown。formal/security始终false。真实规模执行前必须连接受审查的持久记录、资源监督和episode事务，不能仅依据新预算允许160/159次而直接启动长任务。

## 验证记录

首轮26项通过（15.68秒）：真实单机组reference与旧阶段证据一致、actual两级结果、双UID并列解按顺序决胜，及超时/缺界/缺变量/options漂移、pipeline中断、审计失败、规模/UID/小时/预算错配。

新增21 UID合成reference完整23阶段通过（9.77秒），实际调用23次，全部UID按排序保留，结果request=0、每机组generation=10MW；这是跨旧20调用cap的合成证明，不是RTS规模认证。旧reference/actual/core及资源/清单相关回归184项通过（69.97秒）。

独立pre-seal提出资源派生源码身份闭包和finalization失败丢失证据两项finding，已修正并经只读复核闭合。最终36项通过（39.52秒、exit0），还包含21 UID actual完整22阶段、reference/actual连续两小时、旧入口拒绝新预算，以及最大模型构建后的身份漂移在native前停止。最终两条21 UID路径都是合成LP，不能替代RTS完整规模和资源测量。

`git diff --check`通过；reference selector与旧native candidate逐bytes/hash匹配既有`gurobi_four_thread_probe1_evidence.json`。actual selector本轮未编辑，当前SHA256为`57953126a88f7516b328f23f6e3e72e4660a771fc2fac9d5e170a0a3a2071957`（不在上述索引中，不声称由该索引核验）。新内核仍待进程/持久调用记账和episode连接，正式门保持。
