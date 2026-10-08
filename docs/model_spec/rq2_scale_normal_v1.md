# 显式资源计划下的normal数值执行与回放

状态：DRAFT_NONAUTHORITATIVE。只处理normal数值内核的声明预算，不提供正式运行入口或工程认证。

## 目标与已有实现复用

旧`NormalExecutionBudget`保留单solve 30秒、normal累计60秒上限，旧ordered adapter继续固定15秒；已有H25声明和结果不变。新增`scale_normal.py`、`scale_normal_budget.py`、`scale_normal_native.py`和`rq2_gurobi_declared_normal.py`允许按完整原始资源计划声明normal数值预算。新增`scale_normal_replay.py`只读检查数值记录。

构模、连续网侧状态、输入摘要、赋值和terminal witness沿用ordered实现。新native的`_solve`函数AST与旧ordered版本完全一致；新adapter保持Gurobi 13.0.2、Pyomo 6.10.1、direct接口、单线程、seed=0、gap=1e-8及三项1e-9容差，求解时限改为显式正值。kernel进一步要求该时限恰好等于`NormalWork.seconds_per_solve`。不加入重试、warm start或新的求解算法。

## 原始声明与数值预算

`NormalResourcePlan`保存完整normals、episodes、envelopes和SerialResourceBudget。`budget_for_task`通过既有`check_resource_contract`重算一致性，选择唯一normal及其envelope，将完整报告与资源实现摘要绑定进预算。`bind_plan`在执行前及每次输入检查重算，并核对实际normal输入摘要、完整source_hours、机组UID及carry的split标签。该标签核对不认证原始公开来源或经验训练/测试划分；source hours使用ContinuousNormalInputs坐标，不推断raw零基索引。

`ScaleNormalBudget`独立命名并绑定NormalWork、TaskEnvelope和资源合同摘要。数值时限、horizon、规模及线程必须与声明对应；normal累计wall分配不得少于solver预留或超过任务wall，payload分配不得超过archive预算。working-set采样上限独立声明，不能与Job commit容量互相替代。

数值累计wall覆盖本次kernel的准备、三次构模、solve/load、canonical赋值及witness检查；不覆盖source包装、持久化、独立回放与整个进程关闭。TaskEnvelope的non_solver_seconds是调用者对全任务额外成本的声明，尚未通过数值kernel证明充分。完整资源清单的一致性也不证明所有研究任务均已列齐。

## 记录与回放

新结果type为`ScaleNormalExecutionResult`；core身份绑定完整预算、spec、规模及新实现依赖。保留单次调用计数、未完成调用unknown、原生界、目标、残差、整数误差、witness及资源失败记录。`normal_accepted`仍要求单次原生最优、全部数值检查及terminal witness通过，超时不变成不可行。

`export_record`只编码新owned结果。`replay_record`要求外部字节SHA、结果身份、回放身份、完整独立输入/spec/budget/原始plan；不从结果恢复预算。它重新构模，通过既有`grid_evidence_replay._replay`纯数值函数复算赋值、目标、残差和optimal flag，并重算witness及记录的资源/调用/验收一致性。新入口独立admit完整ScaleNormalBudget，不使用旧GridDevelopmentBudget的缩水投影。返回诊断字典，不返回可执行carry或solver结果。

全部formal/security/source-authentication/native-authentication/resource-authentication标志保持false。历史时间与内存只校验记录一致性；独立回放不证明当时真的执行过。只有声明预算较长，不意味着本轮做过长任务或已获得H25最优解。

## 验证及下一连接

`tests/test_rq2_scale_normal_v1.py`首轮37项通过（30.27秒）。600秒spec、600秒solve预留和720秒normal wall通过假求解器原样传递；实际direct Gurobi只运行一秒上限的两小时单机组合成例，目标40并完成零solver回放。另覆盖旧type/adapter拒绝、原始plan与实际输入不符、时间/数值选项漂移、原生失败、资源超限和重hash篡改。native算法AST一致性由测试直接比较。

相关旧`test_rq2_normal_execution_gurobi_ordered_v1.py`、`test_rq2_grid_evidence_replay_v1.py`、`test_rq2_execution_resource_contract_v1.py`共139项通过（57.35秒）。补充四个新模块源码漂移、旧result tag自洽重hash拒绝及pipeline中断后unknown调用数后，新全组43项通过（37.00秒）。回放继承raw/witness错误先独立重算，再校验kernel错误词汇；raw缺失必须有pipeline错误记录。命令均为compute Python `-B -m pytest -q -p no:cacheprovider`，无长求解。

旧normal基础/ordered内核、ordered native、ordered adapter、H25配置及H25 replay共六个文件的bytes/SHA与`gurobi_ordered_task_attempt1_evidence.json`保留索引一致。`git diff --check`通过。

独立预审随后发现继承raw/witness错误按值过滤会漏检重复项，已改为逐次精确消费；缺少occurrence记错，剩余错误再过kernel词汇检查。新增两类重复错误自洽重hash反例；首轮13通过/1失败源于raw测试用了本来不可完整回放的异常记录，改为非fixed angle扰动的完整无效赋值后，最终受影响14项通过、31项未选择（23.43秒）。筛选表达式为`duplicate_inherited or native_failure or actual_tiny or declared_long or interruption`；前述43项不表述为最后修复后的全组结果。

该模块尚未接入现有source-bound持久worker/controller，也未改变episode内层phase的旧进程cap。下一连接须复用现有source核验及监督原语，显式固定新预算/结果类型与回放身份，覆盖source准备、archive与独立回放的整体成本；不再重新开发数值核或通用进程监督。此连接和真实normal最优性仍是实际规模执行的前置，科学参数/删失协议继续独立待登记。
